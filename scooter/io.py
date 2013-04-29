
def charstream(hl):
    while True:
        c = hl.read(1)
        if not c: break
        yield c

