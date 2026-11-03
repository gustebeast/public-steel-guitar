/* pitchrun <file.f32> [fs]: run the detector over raw float32 mono samples (default 48 kHz)
   and print one line per frame: time s, Hz (0 unvoiced), clarity, envelope, event, steady. */
#include <stdio.h>
#include <stdlib.h>

#include "pitch.h"

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: pitchrun <file.f32> [fs]\n");
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        perror(argv[1]);
        return 1;
    }
    static pitch_t p;
    pitch_init(&p, argc > 2 ? (float)atof(argv[2]) : 48000.0f);
    static float buf[960];
    pitch_frame_t fr[64];
    size_t n;
    while ((n = fread(buf, sizeof buf[0], 960, f)) > 0) {
        int k = pitch_push(&p, buf, (int)n, fr, 64);
        for (int i = 0; i < k; i++)
            printf("%.5f %.3f %.3f %.4g %s %d\n", fr[i].t, fr[i].hz, fr[i].clarity, fr[i].env,
                   fr[i].event == PITCH_ON ? "ON" : fr[i].event == PITCH_OFF ? "OFF" : "-", fr[i].steady);
    }
    fclose(f);
    return 0;
}
