% textbook.p
% Baseline Verification Dataset in FOF Format

fof(textbook_1, conjecture, ( (a => b) => ((~a => b) => b) )).
fof(textbook_2, conjecture, ( (~![X]: r(X)) => (?[X]: ~r(X)) )).
fof(textbook_3, conjecture, ( (~?[X]: r(X)) => (![X]: ~r(X)) )).
fof(textbook_4, conjecture, ( (![X]: ?[Y]: (r1(X) & r2(Y))) => ((![X]: r1(X)) & (?[X]: r2(X))) )).
fof(textbook_5, conjecture, ( (![X]: (r1(X) => r2(X))) => ((![X]: r1(X)) => (![X]: r2(X))) )).
fof(textbook_6, conjecture, ( (?[X]: ![Y]: r(X,Y)) => (![Y]: ?[X]: r(X,Y)) )).
fof(textbook_7, conjecture, ( (![X]: r1(X)) => ((![X]: r2(X)) => (![Y]: (r1(Y) & r2(Y)))) )).
fof(textbook_8, conjecture, ( (?[X]: r1(X)) => (?[X]: (r1(X) | r2(X))) )).