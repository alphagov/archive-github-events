# Archive GitHub Events Lambda #

Lambda function which writes GitHub events into S3.

## GitHub Webhook ##

GitHub provide a Webhook to receive events from your organisation. This
repository creates an API Gateway endpoint to receive calls from that webhook
and pass them on to a Lambda function for archiving.

### Event Parsing

The [Lambda](src/archive_event.py) adds a new `timestamp` field to the root of
the JSON object and also goes through the keys and removes any ending `_url` -
these add a lot of _extra_ data that doesn't need to be added to ingested.

If parsing fails - then the original event will get sent to S3.
