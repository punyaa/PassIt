# Single-AZ PostgreSQL 16 for the prototype. Not publicly accessible: only tasks in
# task-sg can connect, so migrations run as a one-off ECS task, never from a laptop.

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "main" {
  name       = "passit-${var.environment}"
  subnet_ids = var.subnet_ids

  tags = { Name = "passit-${var.environment}" }
}

resource "aws_db_instance" "main" {
  identifier             = "passit-${var.environment}"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.instance_class
  allocated_storage      = 20
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = "passit"
  username               = "passit"
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false

  multi_az                = false
  backup_retention_period = 1
  skip_final_snapshot     = true
  apply_immediately       = true

  tags = { Name = "passit-${var.environment}" }
}

# Connection string consumed by ECS tasks and the release Lambda via SSM.
resource "aws_ssm_parameter" "database_url" {
  name  = "/passit/${var.environment}/database-url"
  type  = "SecureString"
  value = "postgresql+psycopg://${aws_db_instance.main.username}:${random_password.db.result}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"

  tags = { Name = "passit-${var.environment}-database-url" }
}
