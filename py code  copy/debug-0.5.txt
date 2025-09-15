print("TESTING FILE I/O AND PLOTTING")

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

print("✓ Matplotlib backend set to Agg (non-interactive)")

# Test basic plotting without display
try:
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    
    plt.figure()
    plt.plot(x, y)
    plt.title('Test Plot')
    
    # Try to save (this might be where MPE fails)
    plt.savefig('test_plot.png')
    plt.close()
    
    print("✓ Plot creation and save successful")
    
except Exception as e:
    print(f"✗ Plotting failed: {e}")

# Test file writing
try:
    test_data = np.array([[1, 2, 3], [4, 5, 6]])
    np.savetxt('test_output.csv', test_data, delimiter=',')
    print("✓ File writing successful")
except Exception as e:
    print(f"✗ File writing failed: {e}")

print("FILE I/O TEST COMPLETE")
