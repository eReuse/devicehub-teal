class NestedLookup:
    @staticmethod
    def __new__(cls, document, references, operation):
        """Lookup a key in a nested document, return a list of values
        From https://github.com/russellballestrini/nested-lookup/ but in python 3
        """
        return list(NestedLookup._nested_lookup(document, references, operation))

    @staticmethod
    def key_equality_factory(key_to_find):
        def key_equality(key, _):
            return key == key_to_find

        return key_equality

    @staticmethod
    def is_sub_type_factory(type):
        def _is_sub_type(_, value):
            return is_sub_type(value, type)

        return _is_sub_type

    @staticmethod
    def key_value_equality_factory(key_to_find, value_to_find):
        def key_value_equality(key, value):
            return key == key_to_find and value == value_to_find

        return key_value_equality

    @staticmethod
    def key_value_containing_value_factory(key_to_find, value_to_find):
        def key_value_containing_value(key, value):
            return key == key_to_find and value_to_find in value

        return key_value_containing_value

    @staticmethod
    def _nested_lookup(document, references, operation):  # noqa: C901
        """Lookup a key in a nested document, yield a value"""
        if isinstance(document, list):
            for d in document:
                for result in NestedLookup._nested_lookup(d, references, operation):
                    yield result

        if isinstance(document, dict):
            for k, v in document.items():
                if operation(k, v):
                    references.append((document, k))
                    yield v
                elif isinstance(v, dict):
                    for result in NestedLookup._nested_lookup(v, references, operation):
                        yield result
                elif isinstance(v, list):
                    for d in v:
                        for result in NestedLookup._nested_lookup(
                            d, references, operation
                        ):
                            yield result


def is_sub_type(value, resource_type):
    try:
        return issubclass(value, resource_type)
    except TypeError:
        return issubclass(value.__class__, resource_type)


def get_nested_dicts_with_key_value(parent_dict: dict, key, value):
    """Return all nested dictionaries that contain a key with a specific value. A sub-case of NestedLookup."""
    references = []
    NestedLookup(
        parent_dict, references, NestedLookup.key_value_equality_factory(key, value)
    )
    return (document for document, _ in references)


def get_nested_dicts_with_key_containing_value(parent_dict: dict, key, value):
    """Return all nested dictionaries that contain a key with a specific value. A sub-case of NestedLookup."""
    references = []
    NestedLookup(
        parent_dict,
        references,
        NestedLookup.key_value_containing_value_factory(key, value),
    )
    return (document for document, _ in references)
