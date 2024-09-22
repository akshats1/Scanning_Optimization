# Scanning_Optimization
Scanning Optimization PI5

```bash
[Start]
   |
[Initialize Variables]
   |
[Configure Camera]
   |
+---------------------------+
|   [Loop i from 0 to 6]   |
+---------------------------+
   |
[Capture Image]
   |
[Calculate Variance]
   |
[Check Maximum Variance]
   |
   +---(current_variance > max_variance)---+
   |                                         |
[Update max_variance and max_z]            |
   |                                         |
   +---(i >= initial_steps and current_variance < max_variance - threshold)---+
   |                                                                         |
[Break Loop]                                                          [Direction is None]
                                                                           |
                                                                    +-------------+
                                                                    |  Determine  |
                                                                    |  Direction   |
                                                                    +-------------+
                                                                           |
[Move Z-Axis] <------------------------------------> [End Loop]
   |
[Adjust Z Position]
   |
[End]

```