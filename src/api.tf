data "aws_caller_identity" "current" {}
data "aws_region" "current" {
  current = true
}

resource "aws_api_gateway_rest_api" "github_webhook_api" {
  name = "GithubWebhookAPI"
  description = "API to collect Github Webhook events and archive them"
}

resource "aws_api_gateway_resource" "webhook_resource" {
  rest_api_id = "${aws_api_gateway_rest_api.github_webhook_api.id}"
  parent_id = "${aws_api_gateway_rest_api.github_webhook_api.root_resource_id}"
  path_part = "{orgname}"
}

resource "aws_api_gateway_method" "webhook_method" {
  rest_api_id = "${aws_api_gateway_rest_api.github_webhook_api.id}"
  resource_id = "${aws_api_gateway_resource.webhook_resource.id}"
  http_method = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "webhook_lambda_integration" {
  rest_api_id = "${aws_api_gateway_rest_api.github_webhook_api.id}"
  resource_id = "${aws_api_gateway_resource.webhook_resource.id}"
  http_method = "${aws_api_gateway_method.webhook_method.http_method}"
  type = "AWS_PROXY"
  uri = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${aws_lambda_function.archive_github_events.function_name}/invocations"
  integration_http_method = "POST"
}

resource "aws_api_gateway_deployment" "github_webhook_deployment" {
  depends_on = [
    "aws_api_gateway_method.webhook_method",
    "aws_api_gateway_integration.webhook_lambda_integration"
  ]
  rest_api_id = "${aws_api_gateway_rest_api.github_webhook_api.id}"
  stage_name = "api"
}

resource "aws_api_gateway_method_response" "200" {
  rest_api_id = "${aws_api_gateway_rest_api.github_webhook_api.id}"
  resource_id = "${aws_api_gateway_resource.webhook_resource.id}"
  http_method = "${aws_api_gateway_method.webhook_method.http_method}"
  status_code = "200"
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id   = "AllowExecutionFromAPIGateway"
  action         = "lambda:InvokeFunction"
  function_name  = "${aws_lambda_function.archive_github_events.function_name}"
  principal      = "apigateway.amazonaws.com"
  source_arn     = "arn:aws:execute-api:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.github_webhook_api.id}/*/${aws_api_gateway_integration.webhook_lambda_integration.integration_http_method}${aws_api_gateway_resource.webhook_resource.path}"
}

output "webhook_url" {
  value = "https://${aws_api_gateway_deployment.github_webhook_deployment.rest_api_id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_deployment.github_webhook_deployment.stage_name}"
}
