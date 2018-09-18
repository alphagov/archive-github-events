resource "aws_s3_bucket" "github_events_bucket" {
  bucket        = "${var.github_events_s3_bucket_name}"
  force_destroy = true
  acl           = "private"

  versioning = {
    enabled = true
  }
}

data "archive_file" "lambda" {
  type = "zip"
  source_file = "archive_event.py"
  output_path = "lambda.zip"
}

resource "aws_lambda_function" "archive_github_events" {
  filename = "${data.archive_file.lambda.output_path}"
  function_name = "archive_github_events"
  role = "${aws_iam_role.github_archivist.arn}"
  handler = "archive_event.lambda_handler"
  runtime = "python3.6"
  source_code_hash = "${base64sha256(file("${data.archive_file.lambda.output_path}"))}"
  publish = true
  environment {
    variables = {
      GITHUB_SECRET  = "${var.github_secret}"
      S3_BUCKET_NAME = "${aws_s3_bucket.github_events_bucket.id}"
    }
  }
}

data "aws_iam_policy_document" "write_github_events_policy_doc" {
  statement {
    sid = "WriteOnlyAccess"
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.github_events_bucket.arn}/*",
    ]
  }
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "write_github_events" {
  name   = "write_github_events"
  policy = "${data.aws_iam_policy_document.write_github_events_policy_doc.json}"
}

resource "aws_iam_role_policy_attachment" "write_github_events_attachment" {
  role       = "${aws_iam_role.github_archivist.id}"
  policy_arn = "${aws_iam_policy.write_github_events.arn}"
}

resource "aws_iam_role_policy_attachment" "aws_basic_lambda_execution_role" {
  role       = "${aws_iam_role.github_archivist.id}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role" "github_archivist" {
  name = "github_archivist"
  assume_role_policy = "${data.aws_iam_policy_document.lambda_assume_role.json}"
}

