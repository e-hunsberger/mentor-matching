# mentor-matching

## Local setup and run using uv (recommended)

To install uv, run the following in powershell:

```powershell -ExecutionPolicy ByPass - "irm hhps://astral.sh/uv/install/ps1 | iex" ```

then close and reopen all Powershell and Command Line windows. 

Create the environment (not encessarily in Powershell):

```uv venv --python 3.12.9```

This will create the environment folder called `.venv` in the directory you run the command, downloading you specified python version. If you encounter an invalid certificate error, run

```uv venv --python 3.12.9 --allow-insecure-host github.com --allow-insecure-host pypi.org --allow insecure-host files.pythonhosted.org```

Activate with the following:

Windows: ```.venv\Scripts\activate```

Then install packages from ```requirements.txt```

```uv pip install -r requirements.txt```

To install packages in the future use

```uv pip install [package name]```

Don't forget to add the additional package to requirements.txt. To check which version was install used

```uv pip show [package name]```

To autostrip the nb output

```uv run nbstripout --install```


## Local setup and run using conda

'conda env create -f env.yml'

To activate the env 

'~\miniconda3\condabin\activate mentor-matching'