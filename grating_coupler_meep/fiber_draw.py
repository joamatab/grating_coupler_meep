"""

8.2 SMF core diameter comes from
https://www.corning.com/media/worldwide/coc/documents/Fiber/SMF-28%20Ultra.pdf

"""

from functools import partial

import meep as mp
import numpy as np

nm = 1e-3
nSi = 3.47
nSiO2 = 1.45


def draw_grating_coupler_fiber(
    period: float = 1.5,
    fill_factor: float = 0.5,
    fiber_angle_deg: float = 15.0,
    fiber_xposition: float = 1.0,
    fiber_core_diameter: float = 8.2,
    fiber_numerical_aperture: float = 0.14,
    fiber_nclad: float = nSiO2,
    resolution: int = 64,  # pixels/um
    ncore: float = nSi,
    nclad: float = nSiO2,
    nsubstrate: float = nSi,
    n_periods: int = 24,
    box_thickness: float = 3.0,
    core_thickness: float = 220 * nm,
    wavelength: float = 1.55,
    etch_depth: float = 70 * nm,
):
    """
    Draw grating coupler with fiber.

    based on https://github.com/simbilod/grating_coupler_meep/blob/master/fiber/gc_outcoupler2.py

    na**2 = ncore**2 - nclad**2

    ncore = sqrt(na**2 + ncore**2)


    Args:
        period: grating coupler period

    """
    substrate_thickness = 1.0
    hair = 4
    core_material = mp.Medium(index=ncore)
    clad_material = mp.Medium(index=nclad)

    dgap = period * (1 - fill_factor)
    dtaper = 12
    dbuffer = 0.5
    dpml = 1

    # Fiber; semi-hardcoded
    # Fiber parameters, from SMF-633-4/125-1-L or PMF-633-4/125-0.25-L
    fiber_clad = 120
    fiber_angle = np.radians(fiber_angle_deg)
    haircore = 2
    hfiber_geom = 100  # Some large number to make fiber extend into PML

    fiber_ncore = (fiber_numerical_aperture ** 2 + fiber_nclad ** 2) ** 0.5
    fiber_clad_material = mp.Medium(index=fiber_nclad)
    fiber_core_material = mp.Medium(index=fiber_ncore)

    # MEEP's computational cell is always centered at (0,0), but code has beginning of grating at (0,0)
    sxy = 2 * dpml + dtaper + period * n_periods + 2 * dbuffer  # sx here
    sz = (
        2 * dbuffer
        + box_thickness
        + core_thickness
        + hair
        + substrate_thickness
        + 2 * dpml
    )  # sy here
    # comp_origin_x = dpml + dbuffer + dtaper
    comp_origin_x = 0
    # meep_origin_x = sxy/2
    # x_offset = meep_origin_x - comp_origin_x
    # x_offset = 0
    # comp_origin_y = dpml + substrate_thickness + box_thickness + core_thickness/2
    # comp_origin_y = 0
    # meep_origin_y = sz/2
    # y_offset = meep_origin_y - comp_origin_y
    y_offset = 0

    # x_offset_vector = mp.Vector3(x_offset,0)
    # offset_vector = mp.Vector3(x_offset, y_offset)
    offset_vector = mp.Vector3(0, 0, 0)

    Si = mp.Medium(index=nsubstrate)

    # We will do x-z plane simulation
    cell_size = mp.Vector3(sxy, sz)

    geometry = []

    # Fiber (defined first to be overridden)

    # Core
    # fiber_offset = mp.Vector3(fiber_xposition + extrax, core_thickness/2 + hair + haircore + extray) - offset_vector
    geometry.append(
        mp.Block(
            material=fiber_clad_material,
            center=mp.Vector3(x=fiber_xposition) - offset_vector,
            size=mp.Vector3(fiber_clad, hfiber_geom),
            e1=mp.Vector3(x=1).rotate(mp.Vector3(z=1), -1 * fiber_angle),
            e2=mp.Vector3(y=1).rotate(mp.Vector3(z=1), -1 * fiber_angle),
        )
    )
    geometry.append(
        mp.Block(
            material=fiber_core_material,
            center=mp.Vector3(x=fiber_xposition) - offset_vector,
            size=mp.Vector3(fiber_core_diameter, hfiber_geom),
            e1=mp.Vector3(x=1).rotate(mp.Vector3(z=1), -1 * fiber_angle),
            e2=mp.Vector3(y=1).rotate(mp.Vector3(z=1), -1 * fiber_angle),
        )
    )

    # clad
    geometry.append(
        mp.Block(
            material=clad_material,
            center=mp.Vector3(0, haircore / 2) - offset_vector,
            size=mp.Vector3(mp.inf, haircore),
        )
    )

    # waveguide
    geometry.append(
        mp.Block(
            material=core_material,
            center=mp.Vector3(0, 0) - offset_vector,
            size=mp.Vector3(mp.inf, core_thickness),
        )
    )

    # grating etch
    for i in range(n_periods):
        geometry.append(
            mp.Block(
                material=clad_material,
                center=mp.Vector3(i * period + dgap / 2, etch_depth / 2)
                - offset_vector,
                size=mp.Vector3(dgap, etch_depth),
            )
        )

    geometry.append(
        mp.Block(
            material=clad_material,
            center=mp.Vector3(sxy - comp_origin_x - 0.5 * (dpml + dbuffer), 0)
            - offset_vector,
            size=mp.Vector3(dpml + dbuffer, core_thickness),
        )
    )

    # BOX
    geometry.append(
        mp.Block(
            material=clad_material,
            center=mp.Vector3(0, -0.5 * (core_thickness + box_thickness))
            - offset_vector,
            size=mp.Vector3(mp.inf, box_thickness),
        )
    )

    # Substrate
    geometry.append(
        mp.Block(
            material=Si,
            center=mp.Vector3(
                0,
                -0.5 * (core_thickness + substrate_thickness + dpml + dbuffer)
                - box_thickness,
            )
            - offset_vector,
            size=mp.Vector3(mp.inf, substrate_thickness + dpml + dbuffer),
        )
    )

    # PMLs
    boundary_layers = [mp.PML(dpml)]

    # mode frequency
    fcen = 1 / wavelength

    waveguide_port_center = mp.Vector3(-1 * dtaper, 0) - offset_vector
    waveguide_port_size = mp.Vector3(0, 2 * haircore - 0.2)
    fiber_port_center = (
        mp.Vector3(
            (0.5 * sz - dpml + y_offset - 1) * np.sin(fiber_angle) + fiber_xposition,
            0.5 * sz - dpml + y_offset - 1,
        )
        - offset_vector
    )
    fiber_port_size = mp.Vector3(sxy * 3 / 5 - 2 * dpml - 2, 0)

    # Waveguide source
    sources = [
        mp.EigenModeSource(
            src=mp.GaussianSource(fcen, fwidth=0.1 * fcen),
            size=waveguide_port_size,
            center=waveguide_port_center,
            eig_band=1,
            direction=mp.X,
            eig_match_freq=True,
            eig_parity=mp.ODD_Z,
        )
    ]

    # symmetries = [mp.Mirror(mp.Y,-1)]
    symmetries = []

    sim = mp.Simulation(
        resolution=resolution,
        cell_size=cell_size,
        boundary_layers=boundary_layers,
        geometry=geometry,
        # geometry_center=mp.Vector3(x_offset, y_offset),
        sources=sources,
        dimensions=2,
        symmetries=symmetries,
        eps_averaging=True,
    )

    # Ports
    waveguide_monitor_port = mp.ModeRegion(
        center=waveguide_port_center + mp.Vector3(x=0.2), size=waveguide_port_size
    )
    waveguide_monitor = sim.add_mode_monitor(
        fcen, 0, 1, waveguide_monitor_port, yee_grid=True
    )
    fiber_monitor_port = mp.ModeRegion(
        center=fiber_port_center - mp.Vector3(y=0.2),
        size=fiber_port_size,
        direction=mp.NO_DIRECTION,
    )
    fiber_monitor = sim.add_mode_monitor(fcen, 0, 1, fiber_monitor_port)
    return sim, fiber_monitor, waveguide_monitor


# remove silicon to clearly see the fiber
draw_grating_coupler_fiber_no_silicon = partial(
    draw_grating_coupler_fiber, ncore=nSiO2, nsubstrate=nSiO2
)


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # sim, fiber_monitor, waveguide_monitor = draw_grating_coupler_fiber()
    sim, fiber_monitor, waveguide_monitor = draw_grating_coupler_fiber_no_silicon()

    sim.plot2D()
    plt.show()
