// Single-threaded OpenMP runtime stubs for iOS.
//
// FEBio calls a handful of OpenMP API functions explicitly
// (omp_get_max_threads, omp_set_num_threads, lock functions, ...).
// The iOS SDK ships no OpenMP runtime, and this spike builds FEBio
// without -fopenmp (so no compiler-generated runtime calls exist —
// only the explicit API calls need symbols). These stubs give the
// solver correct single-threaded semantics: one thread, locks that
// always succeed, wall clock via clock_gettime.
//
// This file is part of the app, NOT a patch to FEBio (FEBio sources
// are unmodified). If a later phase wants multi-threaded solves, the
// real fix is building LLVM's libomp for iOS and dropping this file.

#include <time.h>

int omp_get_thread_num(void) { return 0; }
int omp_get_num_threads(void) { return 1; }
int omp_get_max_threads(void) { return 1; }
int omp_get_num_procs(void) { return 1; }
int omp_get_thread_limit(void) { return 1; }
int omp_in_parallel(void) { return 0; }
int omp_get_level(void) { return 0; }
int omp_get_active_level(void) { return 0; }
int omp_get_team_size(int level) { (void)level; return 1; }
int omp_get_num_teams(void) { return 1; }
int omp_get_team_num(void) { return 0; }
int omp_is_initial_device(void) { return 1; }
int omp_get_dynamic(void) { return 0; }
int omp_get_nested(void) { return 0; }
int omp_get_max_active_levels(void) { return 1; }
int omp_get_default_device(void) { return 0; }
int omp_get_num_devices(void) { return 0; }

void omp_set_num_threads(int n) { (void)n; }
void omp_set_dynamic(int b) { (void)b; }
void omp_set_nested(int b) { (void)b; }
void omp_set_max_active_levels(int n) { (void)n; }
void omp_set_default_device(int n) { (void)n; }
void omp_set_schedule(int kind, int chunk) { (void)kind; (void)chunk; }
void omp_get_schedule(int* kind, int* chunk) { if (kind) *kind = 2; if (chunk) *chunk = 0; }

double omp_get_wtime(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
double omp_get_wtick(void) { return 1e-9; }

/* Lock API: single-threaded, so every lock is uncontended. The lock
   object is an opaque int-sized handle in the real runtime; FEBio
   only stores it and passes it back, so a no-op body is correct. */
void omp_init_lock(void* lock) { (void)lock; }
void omp_init_nest_lock(void* lock) { (void)lock; }
void omp_destroy_lock(void* lock) { (void)lock; }
void omp_destroy_nest_lock(void* lock) { (void)lock; }
void omp_set_lock(void* lock) { (void)lock; }
void omp_set_nest_lock(void* lock) { (void)lock; }
void omp_unset_lock(void* lock) { (void)lock; }
void omp_unset_nest_lock(void* lock) { (void)lock; }
int omp_test_lock(void* lock) { (void)lock; return 1; }
int omp_test_nest_lock(void* lock) { (void)lock; return 1; }
