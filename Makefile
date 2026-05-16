# Makefile para Touchless-UI-RaspberryPi

.PHONY: help build down clean run-ui run-simulation run-camera-test test-hw

help:
	@echo "Comandos disponibles:"
	@echo "  make build             - Construye las imágenes de Docker"
	@echo "  make run-ui            - Ejecuta el sistema REAL (Hardware + Cámara)"
	@echo "  make run-camera-test   - Prueba de Cámara con Hardware SIMULADO"
	@echo "  make run-simulation    - Simulación TOTAL (Cámara y Hardware SIMULADOS)"
	@echo "  make test-hw           - Test guiado e interactivo de los componentes físicos"
	@echo "  make down              - Detiene todos los servicios"
	@echo "  make clean             - Limpieza profunda de Docker"

build:
	docker compose build

# Sistema REAL: Hardware real y Cámara real
run-ui:
	docker compose down
	docker compose run --rm --name touchless_ui touchless_ui

# Prueba de CÁMARA: Cámara real y Hardware simulado (Logs)
run-camera-test:
	docker compose down
	docker compose run --rm --name camera_test camera-test

# Simulación TOTAL: Todo por software (Ideal para desarrollo rápido)
run-simulation:
	docker compose down
	docker compose run --rm --name simulation simulation

# Test guiado e interactivo de PINOUTS y COMPONENTES
test-hw:
	docker compose down
	docker compose run --rm --name hw_test hw-test

down:
	docker compose down

clean:
	docker compose down --rmi all --volumes --remove-orphans
