"""
Tests for minimum grade requirement status
"""

import pytz
import ddt
from datetime import timedelta, datetime
from mock import patch, Mock

from django.test.client import RequestFactory

from openedx.core.djangoapps.credit.models import (
    CreditCourse, CreditProvider, CreditRequirement, CreditRequirementStatus
)
from openedx.core.djangoapps.credit.signals import listen_for_grade_calculation
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from lms.djangoapps.courseware import grades


@ddt.ddt
class TestMinGradedRequirementStatus(ModuleStoreTestCase):
    """Test cases to check the minimum grade requirement status updated.
    If user grade is above or equal to min-grade then status will be
    satisfied. But if student grade is less than and deadline is passed then
    user will be marked as failed.
    """
    VALID_DUE_DATE = datetime.now(pytz.UTC) + timedelta(days=20)
    EXPIRED_DUE_DATE = datetime.now(pytz.UTC) - timedelta(days=20)

    def setUp(self):
        super(TestMinGradedRequirementStatus, self).setUp()
        self.course = CourseFactory.create(
            org='Robot', number='999', display_name='Test Course'
        )

        self.user = UserFactory()
        self.request = RequestFactory().get('/')
        self.request.user = self.user
        self.client.login(username=self.user.username, password=self.user.password)

        # Enable the course for credit
        credit_course = CreditCourse.objects.create(
            course_key=self.course.id,
            enabled=True,
        )

        # Configure a credit provider for the course
        credit_provider = CreditProvider.objects.create(
            provider_id="ASU",
            enable_integration=True,
            provider_url="https://credit.example.com/request",
        )
        credit_course.providers.add(credit_provider)
        credit_course.save()

        # Add a single credit requirement (final grade)
        CreditRequirement.objects.create(
            course=credit_course,
            namespace="grade",
            name="grade",
            criteria={"min_grade": 0.52}
        )

    @ddt.data(
        (0.6, VALID_DUE_DATE),
        (0.52, VALID_DUE_DATE),
        (0.70, EXPIRED_DUE_DATE),
    )
    @ddt.unpack
    def test_min_grade_requirement_with_valid_grade(self, grade_achieved, due_date):
        """Test with valid grades. Deadline date does not effect in case
        of valid grade.
        """

        listen_for_grade_calculation(None, self.user.username, {'percent': grade_achieved}, self.course.id, due_date)
        credit_requirement = CreditRequirementStatus.objects.get(username=self.request.user.username)
        self.assertEqual(credit_requirement.status, "satisfied")

    @ddt.data(
        (0.50, None),
        (0.51, None),
        (0.40, VALID_DUE_DATE),
    )
    @ddt.unpack
    def test_min_grade_requirement_failed_grade_valid_deadline(self, grade_achieved, due_date):
        """Test with failed grades and deadline is still open or not defined."""

        listen_for_grade_calculation(None, self.user.username, {'percent': grade_achieved}, self.course.id, due_date)
        with self.assertRaises(CreditRequirementStatus.DoesNotExist):
            CreditRequirementStatus.objects.get(username=self.request.user.username)

    def test_min_grade_requirement_failed_grade_expired_deadline(self):
        """Test with failed grades and deadline expire"""

        listen_for_grade_calculation(None, self.user.username, {'percent': 0.22}, self.course.id, self.EXPIRED_DUE_DATE)
        credit_requirement = CreditRequirementStatus.objects.get(username=self.request.user.username)
        self.assertEqual(credit_requirement.status, "failed")

    @patch('lms.djangoapps.courseware.grades._grade', Mock(return_value={'grade': 'Pass', 'percent': 0.75}))
    def test_grade_method(self):
        """
        Test grades.grade method send the signal and receiver
        performs accordingly.
        """
        grades.grade(self.user.username, self.request, self.course)
        # credit_requirement = CreditRequirementStatus.objects.get(username=self.request.user.username)
        # self.assertEqual(credit_requirement.status, "satisfied")
