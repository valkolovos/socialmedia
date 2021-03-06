# API Documentation


### Validate Session
`/validate-session` - GET

*Requires Logged In User*

Validates current session.

Request: None

Returns JSON

`{ "email": logged_in user email}`

### Sign Out
`/sign-out` - GET

Logs out current user. If no current user, does nothing.

Returns `signed out`

### Get Messages
`/get-messages` - GET

*Requires Logged In User*

Retrieves current user's messages

Request: None

Returns JSON array with messages

```
[
  {
    "created": create date string,
    "files": [
        signed url for attached file
    ],
    "id": message id,
    "text": Text of message
  }
]
```

### Get Connection Messages
`/get-connection-messages/<connection id>` - GET

*Requires Logged In User*

Retrieves messages for current user's connection specified by `connection id`

Request: None

Returns JSON array with messages

```
[
  {
    "created": create date string,
    "files": [
        signed url for attached file
    ],
    "id": message id,
    "text": Text of message
    "comments": [
      {
        "created": create date string
        "files": [
          signed url for attached file
        ],
        "handle": handle of commenter
        "host": host of commenter
        "id": comment id
        "message_id": message id
        "text": Text of comment
      }
    ],
  }
]
```

### Create Message
`/create-message` - POST

*Requires Logged In User*

Creates a new message for the current user. Will also notify current user's connections that a new message has been created.

Request: multi-part form with required `message` field. Can optionally can contain files to be attached to message.

Returns JSON message

```
{
  "created": create date string,
  "files": [
      signed url for attached file
  ],
  "id": message id,
  "text": Text of message
}
```
