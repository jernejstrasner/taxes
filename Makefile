.PHONY: check-python bootstrap

# Set up the environment
bootstrap: check-python
	@echo "Bootstrapping environment..."
	
	@mkdir -p data
	@curl -o data/Doh_Div_3.xsd http://edavki.durs.si/Documents/Schemas/Doh_Div_3.xsd
	@curl -o data/Doh_KDVP_9.xsd http://edavki.durs.si/Documents/Schemas/Doh_KDVP_9.xsd
	@curl -o data/EDP-Common-1.xsd http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd
	@curl -o data/currency.xml https://www.bsi.si/_data/tecajnice/dtecbs-l.xml

	# Install required python packages
	@pip3 install -r requirements.txt

# This target checks if python3 is installed and conditionally installs it on macOS
check-python:
	@command -v python3 >/dev/null 2>&1 || (echo "Python 3 not found. Installing Python 3..."; \
		UNAME_S=$$(uname -s); \
		if [ "$$UNAME_S" = "Darwin" ]; then \
			brew install python; \
		else \
			echo "Please install Python 3 manually."; \
		fi)
