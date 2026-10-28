/* omp.h — minimal OpenMP API declarations for the iOS build.
 *
 * The iOS SDK ships no OpenMP header or runtime. FEBio (built here
 * without -fopenmp, so no compiler-generated runtime calls exist)
 * includes <omp.h> in exactly one file and explicitly calls only a
 * handful of API functions. This header declares the standard API
 * surface the app provides as single-threaded stubs in
 * App/omp_stub.c. It is part of the build scaffolding, NOT a patch
 * to FEBio: FEBio sources are unmodified, they just find this
 * header first on the include path (see ios.toolchain.cmake).
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct omp_lock_t { void* _lk; } omp_lock_t;
typedef struct omp_nest_lock_t { void* _lk; } omp_nest_lock_t;

typedef enum omp_sched_t {
	omp_sched_static = 1,
	omp_sched_dynamic = 2,
	omp_sched_guided = 3,
	omp_sched_auto = 4
} omp_sched_t;

int omp_get_thread_num(void);
int omp_get_num_threads(void);
int omp_get_max_threads(void);
int omp_get_num_procs(void);
int omp_get_thread_limit(void);
int omp_in_parallel(void);
int omp_get_level(void);
int omp_get_active_level(void);
int omp_get_team_size(int level);
int omp_get_num_teams(void);
int omp_get_team_num(void);
int omp_is_initial_device(void);
int omp_get_default_device(void);
int omp_get_num_devices(void);
int omp_get_max_active_levels(void);
int omp_get_dynamic(void);
int omp_get_nested(void);

void omp_set_num_threads(int n);
void omp_set_dynamic(int b);
void omp_set_nested(int b);
void omp_set_max_active_levels(int n);
void omp_set_default_device(int n);
void omp_set_schedule(omp_sched_t kind, int chunk);
void omp_get_schedule(omp_sched_t* kind, int* chunk);

double omp_get_wtime(void);
double omp_get_wtick(void);

void omp_init_lock(omp_lock_t* lock);
void omp_init_nest_lock(omp_nest_lock_t* lock);
void omp_destroy_lock(omp_lock_t* lock);
void omp_destroy_nest_lock(omp_nest_lock_t* lock);
void omp_set_lock(omp_lock_t* lock);
void omp_set_nest_lock(omp_nest_lock_t* lock);
void omp_unset_lock(omp_lock_t* lock);
void omp_unset_nest_lock(omp_nest_lock_t* lock);
int omp_test_lock(omp_lock_t* lock);
int omp_test_nest_lock(omp_nest_lock_t* lock);

#ifdef __cplusplus
}
#endif
