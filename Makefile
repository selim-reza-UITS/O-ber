up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose up -d --build

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

help:
	@echo "Available commands:"
	@echo "  make up               - Start all services in the background"
	@echo "  make down             - Stop and remove all services"
	@echo "  make build            - Rebuild and start all services"
	@echo "  make logs             - View logs from all services"
	@echo "  make logs-backend     - View logs from the backend service"
	@echo "  make migrate          - Run Django migrations"
	@echo "  make makemigrations   - Create new Django migrations"
	@echo "  make shell            - Open Django shell"
	@echo "  make createsuperuser  - Create Django admin user"
	@echo "  make clean            - Remove __pycache__ and .pyc files"
	@echo "  make test             - Run Django tests"

migrate:
	docker-compose exec backend python manage.py migrate

makemigrations:
	docker-compose exec backend python manage.py makemigrations

shell:
	docker-compose exec backend python manage.py shell

createsuperuser:
	docker-compose exec backend python manage.py createsuperuser

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	docker-compose exec backend python manage.py test
	