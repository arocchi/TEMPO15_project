from casadi import *
from casadi.tools import *
from pylab import *
from manipulator_2links import manipulator_2links
from time import *
import pickle

N = 200     # Control discretization
T = 2.    # End time
h = T/float(N)
M = 1    # Number of IRK4 steps

# Declare variables (use scalar graph)
B = DMatrix(2,1)
B[1] = 1.0
manip = manipulator_2links(B, contacts=True)
manip_perturbed = manipulator_2links(B, contacts=True, K = 4900.0)

u  = manip.u    # control
x  = vertcat([manip.q, manip.dq])  # states

# Formulate the ODE

f = manip.fd_eval

# Discrete time dynamics
#F = simpleRK(f, M)
F = simpleIRK(f, M, 2, "radau")
F.init()

F_sim = simpleIRK(manip_perturbed.fd_eval, M, 2, "radau")
F_sim.init()


# Define NLP variables
W = struct_symMX([
      (
        entry("X",shape=(4,1),repeat=N+1),
        entry("U",shape=(1,1),repeat=N)
      )
])

w = MX(W)

# NLP constraints
g = []

# Build up a graph of integrator calls
for k in range(N):
    # Call the integrator
    [x_next_k] = F([ W["X",k], W["U",k], h ])

    # Append continuity constraints
    g.append(x_next_k - W["X",k+1])

#Add fk constraint
#for k in range(N):
#    g.append(manip.fk_eval([W["X",k][0:2]])[0][1,0])
    
#for k in range(N):
#    g.append(manip.fk_eval([W["X",k][0:2]])[0][1,1])

##Add v constraint
#for k in range(N):
#    g.append(manip.v_eval([W["X",k][0:2],W["X",k][2:4]])[0][1,0])
#    
#for k in range(N):
#    g.append(manip.v_eval([W["X",k][0:2],W["X",k][2:4]])[0][1,1])


# Concatenate constraints
g = vertcat(g)

G = MXFunction([w],[g])
G.init()

A = jacobian(g,w)
Jg = MXFunction([w], [A])
Jg.init()

# Objective function
R = vertcat([vertcat(W['X',2:4]),vertcat(W['U'])])
obj = mul(R.T, R)
obj += 1000*mul( vertcat(W['X',:2]- np.array([pi/2.,0])).T, vertcat(W['X',:2]- np.array([pi/2.,0])))

# Create an NLP solver object
qp = qpStruct(h=H.sparsity(), a=A.sparsity())
qp_solver = QpSolver("qpoases",qp)    # Allocate solver (qpOASES)
qp_solver.init()                       # Initialize the solver

# All constraints are equality constraints in this case
#g_min = DMatrix([0.]*6*N)
#g_min[4*N::] = -0.001;
#g_min[6*N::] = -1.
#g_max = DMatrix([0.0]*6*N)
#g_max[4*N::] = inf;
#g_max[6*N::] = 1.
nlp_solver.setInput(0.0, "lbg")
nlp_solver.setInput(0.0, "ubg")

# Construct and populate the vectors with
# upper and lower simple bounds
w_min = W(-inf)
w_max = W( inf)

# Control bounds
w_min["U",:] = -20.
w_max["U",:] = 20.

w_k = pickle.load(open('npmc_nominal_sol.p'))

x_0 = array([0.,0.,0.,0.])
x_current = x_0

x_final = [[pi/2.,0.,0.,0.]] #upright!
#w_k["U"] = 5.
#w_k["X",:] = x_final*(N+1)
w_min['X',-1] = x_final
w_max['X',-1] = x_final

u_all = []

t = 0
for i in range(N):

    w_min["X",0] = x_current
    w_max["X",0] = x_current

    tic = time()
    
    for i in range(1):
        w_ki = DMatrix(w_k)
        # Pass data to NLP solver
        [g_ki] = G([w_ki])
        [A_ki] = Jg([w_ki])
    
        # Solve the QP
        qp_solver.setInput(H,"h")
        qp_solver.setInput(mul(R.T,mul(R,w_ki)),"g")
        qp_solver.setInput(A_ki,"a")
        qp_solver.setInput(w_min-w_ki,"lbx")
        qp_solver.setInput(w_max-w_ki,"ubx")
        qp_solver.setInput(-g_ki,"lba")
        qp_solver.setInput(-g_ki,"uba")
        qp_solver.evaluate()
        dw_ki = qp_solver.getOutput("x")
        lam_g_ki = qp_solver.getOutput("lam_a")
        lam_w_ki = qp_solver.getOutput("lam_x")
          
        nlp_solver.setInput(w_k,"x0")
        nlp_solver.setInput(w_min,"lbx")
        nlp_solver.setInput(w_max,"ubx")
   
    # Solve the OCP
    toc = time()
    print "solver needed:",toc-tic,"[s] at iteration", i
    
    
    # Extract from the solution the first control
    sol = W(nlp_solver.getOutput("x"))
    u_nmpc = sol["U",0]
    u_all.append(u_nmpc)
    x_k = sol['X']
    
    # Simulate the system with this control
    [x_current] = F_sim([x_current, u_nmpc, h])
  
    t += T/N
    
    # Shift the time to have a better initial guess
    # For the next time horizon
    w_k["X",:-1] = sol["X",1:]
    w_k["U",:-1] = sol["U",1:]
    w_k["X",-1] = sol["X",-1]
    w_k["U",-1] = sol["U",-1]

pickle.dump(np.array(u_all), open('nmpc_sqp_u_perturbed_4900.p','wb'))

#manip.plotTraj(np.array(q_all),t=T/N)
#manip.plotTraj(np.array(q_all),t=T/N,fileName = 'swingup_nmpc.mp4')
#manip.plotTraj(np.array(vertcat(sol["X",:,0:2])).reshape(N+1,2),t=T/N)