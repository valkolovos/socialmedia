from .message_reference import MessageReference

class CommentReference(MessageReference):

    def __repr__(self):
        return f'CommentReference(connection: {{ {repr(self.connection)} }}, ' \
            f'message_id: {self.message_id}, read: {self.read}, created: {self.created})'
