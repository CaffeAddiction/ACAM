#include <iostream>
#include <gmp.h>

// Algoritma 1: Pollard's Rho
void pollard_rho(mpz_t n) {
    mpz_t x, y, d, c, temp;
    mpz_inits(x, y, d, c, temp, NULL);

    mpz_set_ui(x, 2);
    mpz_set_ui(y, 2);
    mpz_set_ui(d, 1);
    mpz_set_ui(c, 1);

    while (mpz_cmp_ui(d, 1) == 0) {
        // x = (x^2 + c) % n
        mpz_mul(temp, x, x);
        mpz_add(temp, temp, c);
        mpz_mod(x, temp, n);

        // y = f(f(y))
        mpz_mul(temp, y, y);
        mpz_add(temp, temp, c);
        mpz_mod(temp, temp, n);
        mpz_mul(temp, temp, temp);
        mpz_add(temp, temp, c);
        mpz_mod(y, temp, n);

        // d = gcd(|x - y|, n)
        mpz_sub(temp, x, y);
        mpz_abs(temp, temp);
        mpz_gcd(d, temp, n);

        if (mpz_cmp(d, n) == 0) {
            std::cout << "Bulunamadi" << std::endl;
            break;
        }
    }

    if (mpz_cmp(d, n) != 0) {
        gmp_printf("Bulunan Carpan: %Zd\n", d);
    }

    fflush(stdout);
    mpz_clears(x, y, d, c, temp, NULL);
}

// Algoritma 2: Trial Division
void trial_division(mpz_t n) {
    mpz_t d, limit;
    mpz_inits(d, limit, NULL);
    
    mpz_sqrt(limit, n);
    mpz_set_ui(d, 2);

    if (mpz_divisible_p(n, d)) {
        gmp_printf("Trial Division Bulunan Carpan: %Zd\n", d);
    } else {
        mpz_set_ui(d, 3);
        while (mpz_cmp(d, limit) <= 0) {
            if (mpz_divisible_p(n, d)) {
                gmp_printf("Trial Division Bulunan Carpan: %Zd\n", d);
                break;
            }
            mpz_add_ui(d, d, 2);
        }
    }
    
    fflush(stdout);
    mpz_clears(d, limit, NULL);
}

// Algoritma 3: Fermat's Factorization
void fermat_factor(mpz_t n) {
    mpz_t a, b2, b, temp, test;
    mpz_inits(a, b2, b, temp, test, NULL);

    mpz_sqrt(a, n);
    mpz_mul(test, a, a);
    
    // n zaten bir tam kareyse
    if (mpz_cmp(test, n) == 0) {
        gmp_printf("Fermat Bulunan Carpan: %Zd\n", a);
        fflush(stdout);
        return;
    }
    
    mpz_add_ui(a, a, 1);

    // AI'nın başarısızlık durumunu yönetebilmesi için makul bir limit
    for (int i = 0; i < 1000000; i++) {
        mpz_mul(b2, a, a);
        mpz_sub(b2, b2, n);
        
        if (mpz_perfect_square_p(b2)) { 
            mpz_sqrt(b, b2);
            mpz_sub(temp, a, b);
            gmp_printf("Fermat Bulunan Carpan: %Zd\n", temp);
            break;
        }
        mpz_add_ui(a, a, 1);
    }
    
    fflush(stdout);
    mpz_clears(a, b2, b, temp, test, NULL);
}

int main(int argc, char* argv[]) {
    if (argc < 3) return 1;

    mpz_t n;
    mpz_init_set_str(n, argv[1], 10);
    int choice = atoi(argv[2]);

    if (choice == 1) pollard_rho(n);
    else if (choice == 2) trial_division(n);
    else if (choice == 3) fermat_factor(n);

    mpz_clear(n);
    return 0;
}