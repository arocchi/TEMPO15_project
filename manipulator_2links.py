from casadi import *
from numpy import *
from matplotlib import pyplot as plt
from matplotlib import animation
import time

class manipulator_2links:
    """
    Ref. Frame:
        y        
        |
        |
        |
        |
        |
        o-------------->x
    """
    def __init__(self, B):
        self.q = SX.sym("q",2)
        self.dq = SX.sym("dq",2)
        self.d = [1.0, 1.0] #[m]
        self.l = [self.d[0]/2.0, self.d[1]/2.0] #[m]
        self.m = [1.0, 1.0] #[Kg]
        self.I = [0.01, 0.01] #[Kg*m^2]
        self.g = 9.81 #[m/s^2]
        self.damping = 0.1*SX.eye(2) #
        
        self.B = B
        self.u = SX.sym("u",B.size2())
        
        
        self.H = SX(2,2)
        a1 = self.I[0] + self.m[0]*self.d[0]**2 + self.I[1] + self.m[1]*self.d[1]**2 + self.m[1]*self.l[0]**2
        a2 = self.m[1]*self.l[0]*self.d[1]
        self.H[0,0] = a1 + 2.0*a2*cos(self.q[1])
        a3 = self.I[1] + self.m[1]*self.d[1]**2
        self.H[0,1] = a2*cos(self.q[1]) + a3
        self.H[1,0] = self.H[0,1]
        self.H[1,1] = a3
        self.H_eval = SXFunction([self.q], [self.H])
        self.H_eval.init()
        
        self.C = SX(2,2)
        self.C[0,0] = -2.0*a2*sin(self.q[1])*self.dq[1]
        self.C[0,1] = -a2*sin(self.q[1])*self.dq[1]
        self.C[1,0] = a2*sin(self.q[1])*self.dq[0]
        self.C[1,1] = 0.0
        self.C_eval = SXFunction([self.q, self.dq], [self.C])
        self.C_eval.init()
        
        self.G = SX(2,1)
        a4 = self.g*(self.m[0]*self.d[0]+self.m[1]*self.l[0])
        a5 = self.g*self.m[1]*self.d[1]
        self.G[0] = a4*cos(self.q[0]) + a5*cos(self.q[0] + self.q[1])
        self.G[1] = a5*cos(self.q[0] + self.q[1])
        self.G_eval = SXFunction([self.q], [self.G])
        self.G_eval.init()
        
        self.fk = SX(2,2) #fk = [p1, p2], pi = [xi, yi]'
        self.fk[0,0] = self.d[0]*cos(self.q[0])
        self.fk[1,0] = self.d[0]*sin(self.q[0])
        self.fk[0,1] = self.fk[0,0] + self.d[1]*cos(self.q[0]+self.q[1])
        self.fk[1,1] = self.fk[1,0] +self.d[1]*sin(self.q[0]+self.q[1])
        self.fk_eval = SXFunction([self.q], [self.fk])
        self.fk_eval.init()
        
        self.fd = mul(self.H.inv(), mul(self.B,self.u)-mul(self.C,self.dq)-self.G-mul(self.damping,self.dq))
        self.fd_eval = SXFunction([vertcat([self.q, self.dq]), self.u], [vertcat([self.dq, self.fd])])
        self.fd_eval.init()   
		
        self.plotter = { 'figure':None, 'axes':None, 'j0':None, 'j1':None, 'l0':None, 'l1':None }
        
    def plot(self,q):
        [ee_fk] = self.fk_eval([q])
        j1 = ee_fk[:,0]
        ee = ee_fk[:,1]
        
        if(self.plotter['figure'] is None):
            self.plotter['figure'] = plt.figure(figsize=(16./2,9./2))
            self.plotter['axes'] = plt.axes(xlim=(-4, 4), ylim=(-4.5/2, 4.5/2))
            self.plotter['figure'].show()
            
            self.plotter['j0'] = plt.Circle((0,0),radius=.1,fc='r')
            self.plotter['j1'] = plt.Circle(j1,radius=.1,fc='r')
            self.plotter['l0'] = plt.Line2D((0, j1[0]), (0,j1[1]), lw=5., 
                                 ls='-', marker='.', 
                                 markersize=10, 
                                 markerfacecolor='r', 
                                 markeredgecolor='r', 
                                 alpha=0.5)
            self.plotter['l1'] = plt.Line2D((j1[0],ee[0]), (j1[1],ee[1]), lw=5., 
                                 ls='-', marker='.', 
                                 markersize=10, 
                                 markerfacecolor='r', 
                                 markeredgecolor='r', 
                                 alpha=0.5)
                                 
            self.plotter['axes'].add_line(self.plotter['l0'])
            self.plotter['axes'].add_line(self.plotter['l1'])
        
        else:
            self.plotter['l0'].set_data(((0, j1[0]), (0,j1[1])))
            self.plotter['l1'].set_data(((j1[0],ee[0]), (j1[1],ee[1])))
            
        plt.draw()
        return [self.plotter['l0'], self.plotter['l1']]
        
    def plotTraj(self,qTraj):
        
        p = lambda i : self.plot(qTraj[i,:])

        anim = animation.FuncAnimation(self.plotter['figure'], 
                                       p, 
                                       frames=qTraj.shape[0], 
                                       interval=1,
                                       blit=True)
        plt.draw()
   
        
if __name__=='__main__':
    manip = manipulator_2links(DMatrix.eye(2))    
    print "l:", manip.l 
    print "d:", manip.d  
    print "m:", manip.m
    print "I:", manip.I
    print "H:", manip.H
    q_eval = [0.0, 0.0]
    print "H_eval:", manip.H_eval([q_eval]) 
    print "C:", manip.C
    dq_eval = [0.0, 0.0]
    print "C_eval:", manip.C_eval([q_eval, dq_eval])
    print "G:", manip.G
    print "G_eval:", manip.G_eval([q_eval])
    print "fk:", manip.fk
    print "fk_eval:", manip.fk_eval([q_eval])
    print "fd:", manip.fd
    u_eval = [0.0, 0.0]
    print "fd_eval:", manip.fd_eval([vertcat([q_eval, dq_eval]), u_eval])
    
    #SIMULATION 
    intg = simpleRK(manip.fd_eval, 10)  
    intg.init()
    N = 1000
    trj = DMatrix(N,2)
    for i in range(N):    
        h_test = 0.01;
        [x_next] = intg([vertcat([q_eval, dq_eval]), u_eval, h_test]);
        q_eval = x_next[0:2]
        dq_eval = x_next[2:4] 
        
        #print "q_eval:", q_eval 
        trj[i,0] = q_eval[0]
        trj[i,1] = q_eval[1] 
        
    manip.plot(trj[0,:])    
    manip.plotTraj(trj)
    
	
