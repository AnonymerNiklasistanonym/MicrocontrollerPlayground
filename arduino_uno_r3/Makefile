SKETCH_DIRS := $(shell find . -type f -name '*.ino' -exec dirname {} \; | sort | uniq)
SKETCH_FILES_INO := $(shell find . -type f -name "*.ino")

# Requires: avr-gcc avr-libc avr-binutils
AVR_INCLUDE := /usr/avr/include
# Requires: arduino IDE or CLI setup
ARDUINO_CORES := $(HOME)/.arduino15/packages/arduino/hardware/avr/1.8.6/cores

ASTYLE_OPTIONS := --style=allman --indent=spaces=2 --align-pointer=type --align-reference=type --suffix=none
CPPCHECK_OPTIONS := --enable=all --language=c++ --std=c++11 -I$(AVR_INCLUDE) -I$(ARDUINO_CORES) --suppress=unusedFunction --suppress=checkersReport --inline-suppr

.PHONY: all analyze clean format

all: format analyze

analyze: $(SRC)
	@echo "Running static analysis on *.ino files..."
	@for dir in $(SKETCH_DIRS); do \
		cppcheck $(CPPCHECK_OPTIONS) --checkers-report=$$dir/cppcheck_report.txt $$dir/*.ino; \
	done
	@echo "Static analysis complete."

# Format all *.ino files
format: $(SKETCH_FILES_INO)
	@echo "Formatting *.ino files..."
	astyle $(ASTYLE_OPTIONS) $^
	@echo "Formatting complete."

# Clean up astyle backup files
clean:
	@echo "Cleaning backup files..."
	@rm -f *.orig
	@find . -name "*.cppcheck_report.txt" -exec rm -f {} \;
	@echo "Cleanup complete."
