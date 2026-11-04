# NFL terminal joint-score research family V1

Decision by Codex, November 3, 2026. New follow-through scope; earlier timed runs remain closed. This specification selects one mathematical research family and one nested control. It authorizes source implementation, fictional-input calculations and independent review only. It does not authorize real fitting, historical forecast generation, scoring, protected-data access or release. Parameter values in synthetic fixtures are test values, never fitted model results.

## Selection and purpose

Select a **negative-binomial total with a key-number-tilted beta-binomial home share**, abbreviated NTBB-K. It is a direct statistical distribution of final REG home/away scores including overtime, not a possession simulator or a claim to reproduce every legally reachable football score. Its usefulness, rare-score support and tie behavior must be tested, not assumed. Integer support alone is not football realism. The nested NTBB control fixes the three key-number tilts at zero; no other challenger/grid is selected.

Reason: this is an estimable small family with an explicit total, score dependence, score-share dispersion and learnable key-number mass, rather than a fabricated Q2 variance. It is computationally inspectable and requires no new operational feed. It can fail. This selection does not claim that these mechanisms explain the current R5 errors, or that this family beats continuous IF or the market.

## Complete law

For nonnegative integer scores h,a, let t=h+a and m=h-a. Reject booleans, nonintegers, negatives and nonfinite inputs. Let mu>0,r>0,0<p<1,c>0 and finite k0,k3,k7.

Total mass:

    q(t)=Gamma(t+r)/(Gamma(r) Gamma(t+1))
         * (r/(r+mu))**r * (mu/(r+mu))**t

Thus E[T]=mu and Var[T]=mu+mu**2/r. Set alpha=p*c and beta=(1-p)*c. Conditional base mass for h=0,...,t:

    b_t(h)=choose(t,h)*B(h+alpha,t-h+beta)/B(alpha,beta)
    z_t(h)=k0*I(2*h-t==0)+k3*I(abs(2*h-t)==3)
           +k7*I(abs(2*h-t)==7)
    Z_t=sum_{j=0}^t b_t(j)*exp(z_t(j))
    P(H=h,A=a)=q(t)*b_t(h)*exp(z_t(h))/Z_t

Use lgamma and log-sum-exp. All three indicators are disjoint. At t=0 the conditional mass is exactly one, so the tie tilt does not change q(0). The tilted conditional must sum to one; un-tilted beta-binomial mass is not simply multiplied without its conditional normalizer. The total marginal is unchanged by the tilts. No home/away points are rounded from continuous IF draws. Home/away swap p->1-p must transpose the joint PMF exactly within declared numerical tolerance, keeping mu,r,c,k unchanged.

This law has infinite total support. It also assigns mass to some historically impossible or extraordinarily rare terminal score pairs; report that support limitation explicitly. No scoring-event, overtime-process, legal-score or market qualification follows from this family. Do not delete unfavorable rare outcomes or relabel this as a drive simulator.

## Inputs and fixed regression form

Proposed future real input packet contains the same-game strictly pre-cutoff frozen IF mean total u>0, frozen canonical Q2 margin q, independently derived rest_H/rest_A, REG game/season/week, KO/seal, full code/config/history/source bindings and an exposure label. It must use one consistent version of the upstream IF/Q2 path; no combining archived R5 means with regenerated R7 state. Missing u/q/rest refuses, not an imputed constant. The package identity binds upstream output digest and the parameter artifact.

    log(mu) = log(u) + b0 + bR*(rest_H+rest_A-14)/14
    logit(p) = g0 + gQ*q/28 + gR*(rest_H-rest_A)/7
    r=exp(lr); c=exp(lc)

Parameter order is (b0,bR,g0,gQ,gR,lr,lc,k0,k3,k7): ten parameters. NTBB control fits the first seven with all k fixed to zero. The denominators14,28,7 are fixed unit scales chosen before results, not learned weights. No extra market anchor, new injury/weather/QB feature, recency grid, calibration layer or automatic R7 point replacement. Expected margin under this family is derived from the actual law; it is NOT forced to equal the 50/50 R7 point blend. Those are distinct scientific candidates.

## Future learning rule, not present execution authority

The proposed fit slice is all exact pinned eligible 2014–2019 REG rows for which upstream features can be constructed chronologically; 2013 is history initialization only. No outcome-dependent eligibility. Eligibility and IDs must be sealed from metadata before feature generation or label access. If an entire slice or feature is unavailable, return a readiness failure; do not quietly choose another fit period. This proposal does not open any historical score data. The real upstream history generation and label-read authority require their own reviewed manifest. Original Q2/2017 evaluation is not reopened by naming a history role. Real 2020/21 remains consumed DEV only, not fitting/calibration data. All 2022/23 EVAL and 2024–26 protections remain.

Minimize negative SUM log likelihood plus Gaussian prior penalties (not average likelihood): b0~N(0,0.5^2), bR~N(0,0.25^2), g0,gQ,gR~N(0,2^2), lr~N(log(20),2^2), lc~N(log(12),2^2), each k~N(0,1). These are explicit, unvalidated research regularizers, not empirically recovered NFL coefficients. Both control and challenger use the same rows/priors for common parameters. No hyperparameter tuning.

One deterministic optimizer run per family: scipy.optimize.minimize L-BFGS-B, start b0=bR=g0=gQ=gR=k0=k3=k7=0, lr=log20, lc=log12; no parameter bounds, maxiter2000, maxfun100000, ftol1e-12, gtol1e-6, maxls40. Use analytic gradients or tested deterministic central differences with step1e-5; method must be frozen with code before real fitting. The first implementation shall use deterministic central differences. Version-pin Python/NumPy/SciPy and BLAS/thread settings in the execution manifest. Require finite objective/parameters, success flag, maximum absolute independent central-difference gradient <=1e-4. No restart/alternate initialization on real data; failure is a failed trial. Nonfinite transforms fail the run, no clipping/silent replacement. No real optimizer invocation is authorized by this specification.

## Tail and consumer contract

Pointwise log PMF for any finite integer observed score pair uses its exact t and full conditional normalizer; there is no truncated-likelihood substitution. For a materialized joint table, start t=0 and increase through at most512. Use negative-binomial survival mass to determine the first N with P(T>N)<=1e-12. Require finite survival and consistent enumerated mass. If no N satisfies this bound, return NUMERICAL_TAIL_LIMIT; do not truncate and renormalize. Returned rows retain their original mass; include tail_mass=sf(N) and enumeration_error. If |sum(rows)+tail_mass-1|>1e-10, refuse. The consumer receives finite-table probabilities as intervals [enumerated event mass, enumerated event mass+tail_mass], not exact values with lost mass.

Because |M|<=T, the omitted first-moment bound can be computed as mu*P(NB(r+1,p_nb)>N-1), p_nb=r/(r+mu). Return this bound with total and margin means. If the moment bound exceeds1e-8 points, expand N within512 or refuse moment outputs. Never silently normalize incomplete rows. Tail parameters exceeding numerical capacity are unsupported, not permission to change the distribution.

All spread/total/moneyline/tie/push summaries derive from the same actual joint rows. Spread selected-side handicap d: home W when H-A+d>0, push equality, loss<0; away uses A-H+d. Total over line L: W when H+A>L, push equality, loss<0. The inputs are exact integer/half-integer decimal strings, not unconstrained float equality. Unknown period/OT/tie settlement refuses settled moneyline, fair odds and EV. Family output is RESEARCH_ONLY/UNQUALIFIED/CERT0; no ALLOW_FIXTURE credential or ENV flag can activate real production use. No real bet recommendation, billing or publication path is introduced.

## Fixed future comparison

If separately authorized, fit exactly NTBB and NTBB-K on the sealed fit slice once, freeze parameter artifacts, then evaluate both on the same exact consumed496 DEV IDs; incomplete496 upstream readiness stops this intended diagnostic before scoring. Primary paired score: mean negative-log-PMF(K)-negative-log-PMF(control), lower favors K. No probability floor or after-result smoothing. Secondary: margin/total discrete CRPS, model mean RMSE and median MAE, home/tie/away categorical Brier, margin masses0,+/-3,+/-7, total/margin central50/80/95% coverage and interval widths, season-specific counts, tail/capability failures. For observed pairs compute exact log PMF even beyond512; table refusal must remain in coverage accounting and cannot drop a scored game. Other probability metrics requiring a refused table remain explicitly missing for the full intended comparison; no complete-success claim.

Use the same preregistered paired season-week cluster bootstrap B10000/PCG64 seed20261103 and game sensitivity seed20261104 as the R7 proposal, preserving season stratification and pooled game-weighted statistic. This is descriptive uncertainty on consumed DEV, not prospective qualification. Existing point-only R5 has no joint PMF and cannot be assigned an invented log score. Market comparisons only use real same-game offered-line/price/timing/rule evidence from the exact96; missing evidence yields NOT_EVALUABLE and no historic ATS/ROI calculation. No winner promotion or next candidate follows automatically.

## Mandatory synthetic implementation tests

Check n=0, symmetric p, home/away transpose, k=0 agreement with scipy beta-binomial, NB marginal identity, total variance identity, tie and3/7 conditional mass movement, extreme-but-valid parameters, finite exact log PMF, table+tail normalization without renormalization, moment bound, cap refusal, bad types, mutation/hash/input/profile/caller mismatches, exact spread/total sign and push partitions, unknown-settlement refusals. Include real producer->shared evidence gate->actual joint capability consumer->atomic temp output/readback, not a saved literal law or imported-but-uninvoked helper. Invalid inputs must cause zero upstream model/solver/network/DB/job/outcome calls. Frozen fabricated fixture values and expected outputs are independently checked before accepting the kernel. Reuse the existing literal-law adapter only as a downstream consumer, not as the new predictive model itself.

## Source and claim limits

Distribution definitions: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.nbinom.html and https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.betabinom.html. These sources support the base probability definitions, not this proposed NFL model's accuracy. The tilting, regression, priors and finite comparison above are Codex's new pre-result research choices. No published performance is attributed to them. Baker/McHale's point-process approach is a different family, not an endorsement or implementation of NTBB-K: https://www.sciencedirect.com/science/article/abs/pii/S0169207012001070.
