function f = post_force2(d,L,a,R)
% Calculates the force exerted on PDMS post from the
% observed displacement of its tip. The calculation for this is
% from Do Eun's thesis.
%
% Usage: f = find_force(d, L, a)
%
% d: the displacement of the post (mm)
% L: the total length of the post (mm)
% a: the height of the tissue on the post (mm)
% f: the returned force (mN)

% Consant
E = 1.7; % elasticity (Young's modulus) of PDMS (MPa)%

% multiply by 1000 to scale to mm
f = 1000 * (3*pi*E*R^4) / (2*a^2*(3*L - a)) * d;