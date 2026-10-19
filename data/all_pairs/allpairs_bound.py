"""Conservative single-run bound on Policy A rejecting its correct original (plan section 3). Standard library only.
Every marginal (range 1) and Z-product (range 2) assertion of A is an empirical mean over N independent ideal shots
(QUTest 0.1.0: qutest/assertions/marginal.py and observable.py compute the mean from the counts and pass when
|estimate - reference| <= atol; the ideal AerSimulator samples final measurements independently). The reference is
the ideal mean rounded to 4 decimals, so a failure needs a deviation of at least theta - 0.00005. Hoeffding with range
2 for every assertion and a union bound over the m = n + n(n-1)/2 assertions give
    P(reject) <= 2 m exp(-N (theta - 0.00005)^2 / 2).
No independence between assertions read from the same histogram is assumed."""
import math
theta, eps = 0.05, 0.00005
print("n | assertions in A | bound at N = 8,000 | bound at N = 2,000")
for n in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
    m = n + n * (n - 1) // 2
    b = lambda N: 2 * m * math.exp(-N * (theta - eps) ** 2 / 2)
    print(f"{n} | {m} | {b(8000):.5f} | {b(2000):.3f}")
