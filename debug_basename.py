import os
filename = "/tmp/sc_full_pipeline_test/Beansclub - Ill Never Find This Sound Of Silence.m4a"
base_name = os.path.splitext(filename)[0]
print(base_name + '.png')
