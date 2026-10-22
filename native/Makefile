CC ?= gcc
CFLAGS = -O3 -march=native -fPIC -fopenmp -Wall -Wextra
LDFLAGS = -shared -fopenmp -lm

TARGET = ../libcachypulse_native.so
SRCS = raytracer.c membench.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
