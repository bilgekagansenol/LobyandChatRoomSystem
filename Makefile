.PHONY: dev install migrate test clean seed docker-build docker-up docker-down

# Development commands
dev: migrate
	@echo "Starting development server..."
	@redis-server --daemonize yes --port 6379 || echo "Redis already running or failed to start"
	python manage.py runserver

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

migrate:
	@echo "Running migrations..."
	python manage.py makemigrations
	python manage.py migrate

test:
	@echo "Running tests..."
	pytest -v

clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/

seed:
	@echo "Seeding database with demo data..."
	python manage.py seed_demo --clear

superuser:
	@echo "Creating superuser..."
	python manage.py createsuperuser

# Docker commands
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

docker-shell:
	@echo "Opening shell in web container..."
	docker-compose exec web bash

# Linting and formatting
lint:
	@echo "Running linting..."
	ruff check .
	black --check .

format:
	@echo "Formatting code..."
	black .
	ruff --fix .

# Production commands
collectstatic:
	@echo "Collecting static files..."
	python manage.py collectstatic --noinput

check:
	@echo "Running Django checks..."
	python manage.py check