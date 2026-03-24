.PHONY: up down logs migrate test shell-api shell-frontend build

# Start all services (detached)
up:
	docker compose up -d --build

# Stop and remove containers
down:
	docker compose down

# Follow logs (all services); pass s=api to filter, e.g. make logs s=api
logs:
	docker compose logs -f $(s)

# Run Alembic migrations inside the api container
migrate:
	docker compose exec api alembic upgrade head

# Run pytest inside the api container
test:
	docker compose exec api pytest $(args)

# Open a shell in the api container
shell-api:
	docker compose exec api bash

# Open a shell in the frontend container
shell-frontend:
	docker compose exec frontend sh

# Build images without starting
build:
	docker compose build
