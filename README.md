# Archive GitHub Events Lambda #

Lambda function which writes GitHub events into S3.

## GitHub Webhook ##

GitHub provide a Webhook to receive events from your organisation. This
repository creates an API Gateway endpoint to receive calls from that webhook
and pass them on to a Lambda function for archiving.
