.PHONY: setup scrape process dev full-run clean

setup:
	docker-compose up -d db ollama
	sleep 5
	# Wait for db to be ready and init schema
	docker-compose exec db psql -U postgres -d marsad -f /docker-entrypoint-initdb.d/init.sql

scrape:
	docker-compose run --rm pipeline python scraper.py --from-year 2020 --to-year 2024

process:
	docker-compose run --rm pipeline python extractor.py
	docker-compose run --rm pipeline python entity_extractor.py
	docker-compose run --rm pipeline python resolver.py

load:
	docker-compose run --rm api python -m api.db.loader

dev:
	docker-compose up -d api frontend

full-run: setup scrape process load dev
	@echo "Full Marsad Al-Idara suite is running!"
	@echo "Frontend: http://localhost:3000"
	@echo "API: http://localhost:8000"

clean:
	docker-compose down -v
	rm -rf data/raw data/extracted data/scrape_state.json
