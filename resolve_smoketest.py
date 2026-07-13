import DaVinciResolveScript as bmd

print("Loading module...")

resolve = bmd.scriptapp("Resolve")

print("Resolve:", resolve)

pm = resolve.GetProjectManager()

print("Project Manager:", pm)