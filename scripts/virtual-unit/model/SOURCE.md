# Source of the model geometry

The files in `source/` are the manufacturer's official structure files for the robot, copied unchanged.

- Repository: https://github.com/m5stack/M5_Hardware
- Folder: `Products/K151_StackChan/Structures` (product K151; the repository has no other folder or revision for this robot)
- Commit: `70fb127275ef0e2da21218d1f01cd305754d35fa` (2026-05-25, "add stackchan structures", the only commit touching the folder when copied)
- Raw URL pattern: `https://raw.githubusercontent.com/m5stack/M5_Hardware/70fb127275ef0e2da21218d1f01cd305754d35fa/Products/K151_StackChan/Structures/<file>`
- License: MIT, Copyright (c) 2021 M5Stack, text in `source/LICENSE` (copied from the repository root at the same commit). Notices: `THIRD-PARTY.md` and `NOTICE`.
- Copied 2026-11-18; re-downloaded and compared on 2026-11-18: all eleven hashes match.

The files are read as data by our own STL reader (`softrender.read_stl`); nothing in them is run.

| File | sha256 |
|---|---|
| `StackChan-Base.stl` | `46990c8941eca02082eca9b11b7dfdefd03d435142c52daee3dc95e1196271c8` |
| `StackChan-BaseCover.stl` | `938ff6547f93ae7f20b26e253e0ee6221d9418c4ce2ea07bce52f8cee0a61495` |
| `StackChan-BearingFixture.stl` | `04f511c46afb82db49657daa8ec624e91d4d26d29712290e26d32084af6bc2f7` |
| `StackChan-LightGuideBar-A.stl` | `05313220a4c3734dd0c412a9de04349e4f9b55024ff3a382ea0d85c1d297d2a3` |
| `StackChan-LightGuideBar-B.stl` | `ba640a41fde8b197a20579814fd8ca94eba44e7b4cbcae3096d6a1e556dd7db2` |
| `StackChan-MainBody.stl` | `5495cd313847c2c135fa0309ee64747b93794e3d464a08e76d518b73b13a3107` |
| `StackChan-ServoArm.stl` | `e530ade0873df01ed5b8bf9275358ccf9ffddb494025f64465bf5efde886c9db` |
| `StackChan-ServoBody.stl` | `c21e35ad812b71aa44933055d3873090ae8c184479edf8e66e1fe595df598e1b` |
| `StackChan-ServoCover.stl` | `f79ff641201fdbde78767cd08b29381ebb0146fa929bdd5e1aa41406e5c6280c` |
| `StackChan-ServoSideCover.stl` | `b4e7906d2f4c5b4d5950c9421b8eadc9ba74b6073f5cee0a67835207d55135ce` |
| `LICENSE` | `44611d917bece311f5c8eeffce83d8bf9e9ca3f815d262f694ff4a7996af50ea` |

Other references used for the assembly and the match check (not copied here): the product's published size drawing
(`Model_Size.png` on the manufacturer's documentation server, K151 page) and three product photos from the same page.
