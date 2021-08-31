class Particle(str):
    def __new__(cls, *args, **kwargs):
        particle_str = args[0]
        obj = str.__new__(cls, " " + particle_str + " ")
        obj.pname = particle_str
        return obj
