from aspc.laundry.models import LaundryMachine, StatusChange
from aspc.college.models import Building

CACHE_SIZE = 20
CONFIDENCE_SIZE = 5
ACTIVE_THRESHOLD = 3.0
machines = LaundryMachine.objects.all()
machine_table = dict([ (machine.building.name+'_'+machine.name, []) for machine in machines])

def add_entry(d, entry, max_size):
    while len(d) >= max_size:
        d.pop()
    d.append(entry)

def classify_status(old_status, cache):
    values = list(cache)
    if values < CONFIDENCE_SIZE:
        return old_status
    mean_value = sum(values)/len(values)
    if mean_value > ACTIVE_THRESHOLD:
        return 1
    return 0

def ws_echo(message):
    message_parts = message.content['text'].split(',')
    dorm_name, machine_name, X, Y, Z = (
        message_parts[0], message_parts[1], float(message_parts[2]), float(message_parts[3]), float(message_parts[4]))
    try:
        dorm = Building.objects.get(name=dorm_name)
        machine = LaundryMachine.objects.get(building=dorm, name = machine_name)
        machine_cache = machine_table[machine.building.name+'_'+machine.name]
        magnitude = (abs(X) + abs(Y) + abs(Z))/3.0
        add_entry(machine_cache, magnitude, CACHE_SIZE)
        status = classify_status(machine.status, machine_cache)
        if machine.status != status:
            StatusChange(machine=machine, status=status).save()
        machine.status = status
        machine.save()
    except Exception as e:
        print e
    print machine_table