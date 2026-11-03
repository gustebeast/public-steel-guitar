CFLAGS = -O2 -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE

pitchrun: pitchrun.c pitch.c pitch.h
	$(CC) $(CFLAGS) -o $@ pitchrun.c pitch.c -lm

clean:
	rm -f pitchrun
