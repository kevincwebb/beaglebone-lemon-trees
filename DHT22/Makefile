TARGETS=read_dht
CFLAGS = -Wall -O2 -pedantic
LFLAGS = -lrt

all: $(TARGETS)

read_dht: read_dht.c
	g++ $(CFLAGS) -o read_dht read_dht.c Beagle_GPIO.cc $(LFLAGS)

clean:
	rm -f $(TARGETS)
