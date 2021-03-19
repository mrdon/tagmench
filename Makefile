.PHONY: run tunnel client help venv db db-migrate db-makemigrations format


# Help system from https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Create python venv
	python3.8 -m venv venv
	venv/bin/pip install pip-tools
	venv/bin/pip-compile
	venv/bin/pip install -r requirements.txt
	
db: ## Logs into psql
	docker-compose exec -e PGPASSWORD=postgres db psql -U postgres -h localhost -p 5432 postgres

format: ## Format the code
	venv/bin/black src
	venv/bin/reorder-python-imports --py38-plus `find src -name "*.py"` || venv/bin/black src --target-version py38



db-makemigrations: ## Creates a migration
	docker-compose run --no-deps web sh -c 'cd / && /alembic/venv/bin/alembic revision --autogenerate -m "replace me"'
	sudo chown $(USER) src/alembic/versions/*

db-migrate: ## Migrate the local database
	docker-compose run --no-deps web sh -c 'cd / && /alembic/venv/bin/alembic upgrade head'

db-reset: ## Set up the database.  Doesn't need docker-compose running.
	docker-compose kill db
	mkdir -p data
	docker-compose rm -fs db
	docker-compose up -d db
	sleep 3
	docker-compose run --no-deps web sh -c 'cd / && /alembic/venv/bin/alembic upgrade head'

db-migrations-prod: ## Run migrations on the prod database
	ssh root@app.thedisturbed.co dokku run tagmench /alembic/venv/bin/alembic upgrade head

logs: ## Tail remote prod logs
	ssh -t root@app.thedisturbed.co dokku logs tagmench -t

up: ## Runs the app using tmux
	docker-compose kill
	docker-compose up -d
	docker-compose logs -f

up-clean: clean build db-reset up ## Resets dev and starts the app

clean: do-clean build db-reset ## Cleans any running or extra files

do-clean:
	docker-compose kill
	rm -rf data

build: ## Builds the app
	docker-compose kill
	DOCKER_BUILDKIT=1 docker build -t tagmench-dev .

tunnel: ## Create tunnel
	ssh -R 80:localhost:8080 ssh.localhost.run
