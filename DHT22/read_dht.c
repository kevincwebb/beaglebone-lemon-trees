/*
 * Copyright (c) 2014, Kevin Webb
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 * this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 * this list of conditions and the following disclaimer in the documentation
 * and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 * contributors may be used to endorse or promote products derived from this
 * software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
*/

#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "Beagle_GPIO.hh"

#define SAMPLES (13000)

struct transition {
    int valid;
    unsigned char to;
    struct timespec when;
};

struct timespec diff(struct timespec start, struct timespec end)
{
	struct timespec temp;
	if ((end.tv_nsec-start.tv_nsec)<0) {
		temp.tv_sec = end.tv_sec-start.tv_sec-1;
		temp.tv_nsec = 1000000000+end.tv_nsec-start.tv_nsec;
	} else {
		temp.tv_sec = end.tv_sec-start.tv_sec;
		temp.tv_nsec = end.tv_nsec-start.tv_nsec;
	}
	return temp;
}

int main(int argc, char **argv) {
    struct timespec before, after, tdiff;
    int i, t, success, attempts, c;
    Beagle_GPIO	gpio;
    struct sched_param params;
    unsigned char values[SAMPLES];
    struct transition transitions[SAMPLES];
    FILE *pin_export;

    int verbose = 0;
    unsigned short pin = Beagle_GPIO::P9_27;
    clockid_t clk_id = CLOCK_REALTIME;

    /* Check for CLI options. Currently just verbose and init flags. */
    while ((c = getopt(argc, argv, "iv")) != -1) {
        switch (c) {
            case 'i':
                /* Export the GPIO pin. 115 is P9_27 (GPIO3_19). */
                pin_export = fopen("/sys/class/gpio/export", "w");
                if (pin_export == NULL) {
                    perror("Couldn't export GPIO pin (/sys/class/gpio/export): ");
                    return 1;
                }
                if (fwrite("115", 1, 3, pin_export) != 3) {
                    perror("Couldn't export gpio pin (write): ");
                    return 1;
                }
                fclose(pin_export);
                return 0;
            case 'v':
                verbose = 1;
                break;
            default:
                fprintf(stderr, "Unknown option: -%c.\n", optopt);
                return 1;
        }
    }

    /* Set maximum, real-time FIFO priority.  This is an attempt to minimize
     * our chances of being context switched while we're in the middle of
     * sampling the sensor. */
    params.sched_priority = sched_get_priority_max(SCHED_FIFO);
    if (sched_setscheduler(0, SCHED_FIFO, &params)) {
        perror("Couldn't set SCHED_FIFO: sched_setscheduler");
    }

    if (verbose) {
        printf("Starting...\n");
        clock_gettime(clk_id, &before);
    }

    attempts = 0;
    success = 0;
    while (!success) {
        /* Bookkeeping.
         * attempts: the number of times we've tried to get a reading.  We
         * might fail if the timing of our pin reads is poor.
         * transitions: records which state the pin was in and for how long. */
        int bit_count = 0;
        int bits[42];
        attempts += 1;
        memset(transitions, 0, sizeof(struct transition) * SAMPLES);

        /* Reset the pin to the high value and then wait for it to settle.
         * Spec sheet says two seconds.  We'll wait three just to be safe. */
        gpio.configurePin(pin, Beagle_GPIO::kOUTPUT);
        gpio.enablePinInterrupts(pin, false);
        gpio.writePin(pin, 1);
        sleep(3);

        /* Initiate a reading. */
        gpio.writePin(pin, 0);
        usleep(5000);
        gpio.writePin(pin, 1);
        usleep(1);

        /* Prepare for reading. */
        gpio.configurePin(pin, Beagle_GPIO::kINPUT);
        gpio.enablePinInterrupts(pin, false);

        /* Read the pin in rapid succession, as quickly as possible. If the
         * state changes, record the transition time. */
        t = 0;
        values[0] = gpio.readPin(pin);
        for (i = 1; i < SAMPLES; ++i) {
            values[i] = gpio.readPin(pin);
            if (values[i] != values[i - 1]) {
                transitions[t].valid = 1;
                transitions[t].to = values[i];
                clock_gettime(clk_id, &transitions[t].when);
                t += 1;
            }
        }

        /* Post-process the transitions and try to interpret whether they were
         * indicating 0's or 1's.  We use 50 usec as the threshold. */
        for (t = 1; t < SAMPLES; ++t) {
            if (!transitions[t].valid)
                break;

            tdiff = diff(transitions[t-1].when, transitions[t].when);

            /* If verbose, print the bit transition timing, marking the ones
             * that have poor/untrustworthy timings. */
            if (verbose) {
                printf("[%d] Transition -> %d tv_sec: %ld, tv_nsec: %ld",
                        t, transitions[t].to, tdiff.tv_sec, tdiff.tv_nsec);

                if (tdiff.tv_nsec < 20000 || tdiff.tv_nsec > 85000) {
                    printf(" **\n");
                } else {
                    printf("\n");
                }
            }

            /* If this was a transition to 0, we should look at the timing and
             * interpret it as a 0/1 bit. */
            if (transitions[t].to == 0) {
                if (tdiff.tv_nsec < 50000) {
                    bits[bit_count] = 0;
                } else {
                    bits[bit_count] = 1;
                }
                bit_count += 1;
            }
        }

        if (verbose) {
            printf("%d bits\n", bit_count);
        }

        /* We need at least 40 bits.  If we didn't get 40, something went
         * wrong, so we'll try again on the next attempt. */
        if (bit_count < 40) {
            continue;
        }

        while (bit_count >= 40) {
            int begin = bit_count - 40;
            int bytes[5], checksum;

            if (verbose) {
                for (i = begin; i < bit_count; ++i) {
                    if ((i - begin) % 8 == 0) {
                        printf("  ");
                    }
                    printf("%d", bits[i]);
                }
                printf("\n");
            }

            memset(bytes, 0, 5 * sizeof(int));

            for (i = 0; i < 5; ++i) {
                for (t = 0; t < 8; ++t) {
                    bytes[i] = bytes[i] << 1;
                    bytes[i] |= bits[(i * 8) + t + begin];
                }
                if (verbose) {
                    printf("  byte %d: %d\n", i, bytes[i]);
                }
            }

            checksum = (bytes[0] + bytes[1] + bytes[2] + bytes[3]) & 0xFF;
            if (verbose) {
                printf("Checksum: %d\n", checksum);
            }

            if (bytes[4] == checksum) {
                int rh = (bytes[0] << 8) + bytes[1];
                int temp = (bytes[2] << 8) + bytes[3];

                if (verbose) {
                    printf("RH: %.1f%%, Temp: %.1fº C (%.1fº F)\n", rh / (10.0),
                        temp / (10.0), (temp * 9.0 / (50.0)) + 32);
                } else {
                    printf("%.1f %.1f\n", rh / (10.0), temp / (10.0));
                }

                success = 1;
                break;
            } else if (verbose) {
                printf("--Bad checksum (%d attempts)\n", attempts);
            }
            bit_count -= 1;
        }
    }

    if (verbose) {
        clock_gettime(clk_id, &after);
        tdiff = diff(before, after);
        printf("Took %ld seconds for a reading. (%d attempts)\n",
                tdiff.tv_sec, attempts);
    }

    /* Clean up: Leave the pin in the idle state when we're done. */
    gpio.configurePin(pin, Beagle_GPIO::kOUTPUT);
    gpio.enablePinInterrupts(pin, false);
    gpio.writePin(pin, 1);

    return 0;
}
