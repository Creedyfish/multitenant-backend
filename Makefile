test-up:
	docker compose -f docker-compose.test.yml -p logisticore-test up

test-down:
	docker compose -f docker-compose.test.yml -p logisticore-test down

test:
	docker compose -f docker-compose.test.yml -p logisticore-test up --abort-on-container-exit
	docker compose -f docker-compose.test.yml -p logisticore-test down