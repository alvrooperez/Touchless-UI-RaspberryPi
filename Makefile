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

# Ejecutar un test específico por nombre (Debe estar UP)
# Ejemplo: make test test_web
test:
	@if [ -z "$(filter-out test,$(MAKECMDGOALS))" ]; then \
		echo "Error: Especifica el nombre del test. Ejemplo: make test test_web"; \
		exit 1; \
	fi
	docker compose exec touchless_ui python3 tests/$(filter-out test,$(MAKECMDGOALS)).py

# Truco para que make no se queje de que el nombre del test no es un comando
%:
	@:

# Limpieza profunda
clean:
	docker compose down --rmi all --volumes --remove-orphans
