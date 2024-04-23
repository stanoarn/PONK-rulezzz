from pydantic import BaseModel


class StringBuildable(BaseModel):
    @classmethod
    def id(cls):
        raise NotImplementedError(f"Please give your class {cls.__name__} an id")

    @classmethod
    def get_direct_children(cls) -> dict[str, type]:
        return {sub.id(): sub for sub in cls.__subclasses__()}

    @classmethod
    def get_final_children(cls) -> list[type]:
        children = cls.__subclasses__()
        for child in children:
            if child.__subclasses__():
                children.remove(child)
                children += child.__subclasses__()
        return children


# might NOT be needed after all
    @classmethod
    def build_from_string(cls, string: str):
        child_id, args = string.split(':')[0], string.split(':')[1:]
        args = {arg.split('=')[0]: arg.split('=')[1] for arg in args}
        return cls.get_direct_children()[child_id](**args)

    @staticmethod
    def parse_string_args(**decorator_kwargs):
        kwargs_transform = {value: (lambda x: x == 'True' if typ == bool else typ)
                            for value, typ in decorator_kwargs.items()}

        def decorate(f):
            def wrapper(*args, **kwargs):
                # modified_kwargs = {
                #     key: (kwargs_transform[key](item) if item.__class__ != decorator_kwargs[key] else item)
                #     for key, item in kwargs.items()}
                # return f(*args, **modified_kwargs)
                return f(*args, **kwargs)
            return wrapper
        return decorate

