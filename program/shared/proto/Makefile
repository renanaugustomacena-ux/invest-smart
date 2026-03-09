PROTO_DIR := .
GEN_DIR := gen
PYTHON_OUT := $(GEN_DIR)/moneymaker_proto
GO_OUT := $(GEN_DIR)/go

.PHONY: all clean python go

all: python go

python:
	mkdir -p $(PYTHON_OUT)
	python -m grpc_tools.protoc \
		-I$(PROTO_DIR) \
		--python_out=$(PYTHON_OUT) \
		--grpc_python_out=$(PYTHON_OUT) \
		--pyi_out=$(PYTHON_OUT) \
		$(PROTO_DIR)/market_data.proto \
		$(PROTO_DIR)/trading_signal.proto \
		$(PROTO_DIR)/execution.proto \
		$(PROTO_DIR)/health.proto
	touch $(PYTHON_OUT)/__init__.py
	@# Fix generated imports to use relative (intra-package) imports.
	@cd $(PYTHON_OUT) && \
		for f in *_pb2*.py; do \
			sed -i 's/^import \([a-z_]*_pb2\) as/from . import \1 as/' "$$f"; \
			sed -i 's/^from \([a-z_]*_pb2\) import/from .\1 import/' "$$f"; \
		done

go:
	mkdir -p $(GO_OUT)
	protoc \
		-I$(PROTO_DIR) \
		--go_out=$(GO_OUT) --go_opt=paths=source_relative \
		--go-grpc_out=$(GO_OUT) --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/market_data.proto \
		$(PROTO_DIR)/trading_signal.proto \
		$(PROTO_DIR)/execution.proto \
		$(PROTO_DIR)/health.proto

clean:
	rm -rf $(GEN_DIR)
