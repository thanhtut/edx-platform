from xmodule.modulestore import Location
from contentstore.utils import get_modulestore
from xmodule.x_module import XModuleDescriptor
from xmodule.modulestore.inheritance import own_metadata


class CourseMetadata(object):
    '''
    For CRUD operations on metadata fields which do not have specific editors on the other pages including any user generated ones.
    The objects have no predefined attrs but instead are obj encodings of the editable metadata.
    '''
    # __new_advanced_key__ is used by client not server; so, could argue against it being here
    FILTERED_LIST = XModuleDescriptor.system_metadata_fields + ['start', 'end', 'enrollment_start', 'enrollment_end', 'tabs', 'graceperiod', '__new_advanced_key__']

    @classmethod
    def fetch(cls, course_location):
        """
        Fetch the key:value editable course details for the given course from persistence and return a CourseMetadata model.
        """
        if not isinstance(course_location, Location):
            course_location = Location(course_location)

        course = {}

        descriptor = get_modulestore(course_location).get_item(course_location)

        for field in descriptor.fields + descriptor.lms.fields:
            if field.name not in cls.FILTERED_LIST:
                course[field.name] = field.read_from(descriptor)

        return course

    @classmethod
    def update_from_json(cls, course_location, jsondict):
        """
        Decode the json into CourseMetadata and save any changed attrs to the db.

        Ensures none of the fields are in the blacklist.
        """
        descriptor = get_modulestore(course_location).get_item(course_location)

        dirty = False

        for k, v in jsondict.iteritems():
            # should it be an error if one of the filtered list items is in the payload?
            if k in cls.FILTERED_LIST:
                continue

            if hasattr(descriptor, k) and getattr(descriptor, k) != v:
                dirty = True
                setattr(descriptor, k, v)
            elif hasattr(descriptor.lms, k) and getattr(descriptor.lms, k) != k:
                dirty = True
                setattr(descriptor.lms, k, v)

        if dirty:
            get_modulestore(course_location).update_metadata(course_location, own_metadata(descriptor))

        # Could just generate and return a course obj w/o doing any db reads, but I put the reads in as a means to confirm
        # it persisted correctly
        return cls.fetch(course_location)

    @classmethod
    def delete_key(cls, course_location, payload):
        '''
        Remove the given metadata key(s) from the course. payload can be a single key or [key..]
        '''
        descriptor = get_modulestore(course_location).get_item(course_location)

        for key in payload['deleteKeys']:
            if hasattr(descriptor, key):
                delattr(descriptor, key)
            elif hasattr(descriptor.lms, key):
                delattr(descriptor.lms, key)

        get_modulestore(course_location).update_metadata(course_location, own_metadata(descriptor))

        return cls.fetch(course_location)
