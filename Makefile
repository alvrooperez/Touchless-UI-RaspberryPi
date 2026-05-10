# Makefile para Touchless-UI-RaspberryPi

.PHONY: help build up down restart logs clean

# Muestra esta ayuda por defecto
help:
	@echo "Comandos disponibles:"
	@echo "  make build    - Construye la imagen de Docker"
	@echo "  make up       - Levanta los contenedores en segundo plano"
	@echo "  make down     - Detiene y elimina los contenedores"
	@echo "  make restart  - Reinicia los contenedores"
	@echo "  make logs     - Muestra los logs en tiempo real"
	@echo "  make clean    - Detiene todo y borra imágenes huérfanas"

# Construir la imagen
build:
	docker compose build

# Levantar el proyecto
up:
	docker compose up -d

# Detener el proyecto
down:
	docker compose down

# Reiniciar
restart:
	docker compose down
	docker compose up -d

# Ver los registros (logs)
logs:
	docker compose logs -f

# Ejecutar tests (Ejemplo: make test o make test FILE=tests/test_web.py)
test:
	@if [ -z "$(FILE)" ]; then \
		echo "Ejecutando todos los tests..."; \
		python3 -m unittest discover tests; \
	else \
		echo "Ejecutando test: $(FILE)"; \
		python3 $(FILE); \
	fi

# Limpieza profunda
clean:
	docker compose down --rmi all --volumes --remove-orphans
