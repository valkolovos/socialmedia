from .post_reference import PostReference

class CommentReference(PostReference):

    def __repr__(self):
        return f'CommentReference(connection: {{ {repr(self.connection)} }}, ' \
            f'post_id: {self.post_id}, read: {self.read}, created: {self.created})'
