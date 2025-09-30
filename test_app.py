#!/usr/bin/env python3

try:
    print("Testing app import...")
    from app import app
    print("SUCCESS: App imported successfully")
    
    print("Testing app creation...")
    print("App object:", app)
    print("App name:", app.name)
    
    print("Testing app run...")
    app.run(debug=True, host='0.0.0.0', port=5000)
    
except Exception as e:
    print("ERROR:", str(e))
    import traceback
    traceback.print_exc()

