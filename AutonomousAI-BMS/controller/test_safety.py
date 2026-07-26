from safety_guard import SafetyGuard


tests = [

    # Normal action
    {
        "heating": 20,
        "cooling": 25
    },

    # Unsafe heating
    {
        "heating": 25,
        "cooling": 26
    },

    # Excessive cooling relaxation
    {
        "heating": 20,
        "cooling": 35
    },

    # Heating/cooling conflict
    {
        "heating": 22,
        "cooling": 22
    }

]


for test in tests:

    result = SafetyGuard.validate(

        proposed_heating=test["heating"],
        proposed_cooling=test["cooling"],

        current_heating=20,
        current_cooling=25
    )

    print("\nProposed:")
    print(test)

    print("Validated:")
    print(result)