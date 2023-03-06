from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import *
from qm.simulate.credentials import create_credentials
from qm import SimulationConfig
from configuration import config
from qm.simulate import LoopbackInterface
import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pyplot as plt
from qualang_tools.loops import from_array
from qualang_tools.results import fetching_tool
from qm.simulate import LoopbackInterface
from qualang_tools.plot import interrupt_on_close
from qualang_tools.results import progress_counter
import numpy as np
from qualang_tools.units import unit

dc0_q2 = config["controllers"]["con1"]["analog_outputs"][8]["offset"]
dc0_q1 = config["controllers"]["con1"]["analog_outputs"][7]["offset"]
ts = np.arange(4, 200, 1)
amps = np.arange(-0.315, -0.298, 0.0002)
n_avgs = 1300000

with program() as iswap:

    I = [declare(fixed) for i in range(2)]
    Q = [declare(fixed) for i in range(2)] 
    I_st = [declare_stream() for i in range(2)]
    Q_st = [declare_stream() for i in range(2)]
    n = declare(int)
    n_st = declare_stream()
    t = declare(int)
    a = declare(fixed)

    with for_(n, 0, n < n_avgs, n+1):
        save(n, n_st)
        with for_(*from_array(t, ts)):
            with for_(*from_array(a, amps)):
                set_dc_offset("q1_z", "single", dc0_q1)
                wait(1000, "q1_z")
                align()
                play("x180_ft", "q2_xy")
                align()
                set_dc_offset("q1_z", "single", a)
                wait(t, "q1_z")
                align()
                set_dc_offset("q1_z", "single", dc0_q1)
                wait(10)
                align()
                measure("readout", "rr1", None, dual_demod.full("rotated_cos", "out1", "rotated_minus_sin", "out2", I[0]),
                        dual_demod.full("rotated_sin", "out1", "rotated_cos", "out2", Q[0]))
                measure("readout", "rr2", None, dual_demod.full("rotated_cos", "out1", "rotated_sin", "out2", I[1]))
                save(I[1], I_st[1])
                save(I[0], I_st[0])
                save(Q[0], Q_st[0])


    with stream_processing():

        # for the progress counter
        n_st.save('n')

        # resonator 1
        I_st[0].buffer(len(ts), len(amps)).average().save("I1")
        Q_st[0].buffer(len(ts), len(amps)).average().save("Q1")

        # resonator 2
        I_st[1].buffer(len(ts), len(amps)).average().save("I2")

# open communication with opx
qmm = QuantumMachinesManager(host="192.168.1.82", port=80)

# simulate the qua program
# job = qmm.simulate(config, iswap, SimulationConfig(15000))
# job.get_simulated_samples().con1.plot()
# plt.show()
qm = qmm.open_qm(config)
job = qm.execute(iswap)
fig, ax = plt.subplots(3)
interrupt_on_close(fig, job)

while job.result_handles.is_processing():
    results = fetching_tool(job, ["n", "I1", "Q1", "I2"], mode="live")
    n, I1, Q1, I2 = results.fetch_all()
    progress_counter(n, n_avgs)

    u = unit()
    ax[0].cla()
    ax[0].pcolor(amps,4*ts, I1)
    ax[0].set_title('q1 - I , n={}'.format(n))
    ax[1].cla()
    ax[1].pcolor(amps,4*ts, Q1)
    ax[1].set_title('q1 - Q , n={}'.format(n))
    ax[2].cla()
    ax[2].pcolor(amps,4*ts, I2)
    ax[2].set_title('q2 - I , n={}'.format(n))
    plt.pause(1.0)
    np.savez('iswap', I1=I1, Q1=Q1, I2=I2, ts=ts, amps=amps)

plt.show()