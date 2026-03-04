def toggle_particles(particles_enabled, set_toast):
    particles_enabled = not particles_enabled
    set_toast(f"Particles: {'ON' if particles_enabled else 'OFF'}")
    return particles_enabled

def toggle_flashes(flashes_enabled, set_toast):
    flashes_enabled = not flashes_enabled
    set_toast(f"Flashes: {'ON' if flashes_enabled else 'OFF'}")
    return flashes_enabled

def toggle_screenshake(screenshake_enabled, set_toast):
    screenshake_enabled = not screenshake_enabled
    set_toast(f"Screenshake: {'ON' if screenshake_enabled else 'OFF'}")
    return screenshake_enabled
