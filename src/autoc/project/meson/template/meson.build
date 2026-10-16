project('@project@', 'c',
  version: '0.1.0',
  meson_version: '>= 1.1',
  default_options: ['warning_level=2']
)

fs = import('fs')
py = import('python').find_installation('python3', required: false)

# Read site configuration if present
site_py = ''
site_pythonpath = ''
if fs.exists('.autoc/meson.site')
  site_lines = fs.read('.autoc/meson.site').strip().split('\n')
  foreach line : site_lines
    if line.startswith('PYTHON = ')
      site_py = line.substring(10, -1)
    elif line.startswith('AUTOC_PYTHONPATH = ')
      site_pythonpath = line.substring(20, -1)
    endif
  endforeach
endif

if site_py != ''
  py = import('python').find_installation(site_py, required: false)
endif

module_name = '@module@'
meson_file = module_name + '.meson'

regen_opt = get_option('regenerate')
has_meson_file = fs.exists(meson_file)

env_cmd = []
if site_pythonpath != ''
  env_cmd = ['env', 'PYTHONPATH=' + site_pythonpath]
endif

if not has_meson_file
  if not py.found()
    error('AutoC generator requires Python 3, but Python was not found and ' + meson_file + ' is missing.')
  endif
  message('Bootstrapping AutoC module ' + module_name)
  if env_cmd.length() > 0
    run_command(env_cmd, py, module_name + '.py', module_name, check: true)
  else
    run_command(py, module_name + '.py', module_name, check: true)
  endif
endif

autoc_file_names = fs.read(meson_file).strip().split()
autoc_sources = files(autoc_file_names)

need_generator = regen_opt.enabled() or (regen_opt.auto() and py.found())

if need_generator
  gen_cmd = []
  if env_cmd.length() > 0
    gen_cmd += env_cmd
  endif
  gen_cmd += [py, '@INPUT@', module_name, '@OUTPUT@']

  module_gen = custom_target(
    module_name + '-generate',
    input: module_name + '.py',
    output: module_name + '.stamp',
    command: gen_cmd,
    build_by_default: true,
  )
  autoc_dep = declare_dependency(
    sources: [autoc_sources, module_gen],
    include_directories: include_directories('.')
  )
else
  autoc_dep = declare_dependency(
    sources: autoc_sources,
    include_directories: include_directories('.')
  )
endif

app_sources = []
if fs.exists('@project@.c')
  app_sources += files('@project@.c')
endif

has_c_sources = false
foreach f : autoc_file_names
  if f.endswith('.c')
    has_c_sources = true
  endif
endforeach

if app_sources.length() > 0 or has_c_sources
  exe = executable('@project@',
    sources: app_sources,
    dependencies: [autoc_dep]
  )
  test('@project@', exe)
endif

doxygen = find_program('doxygen', required: false)
if doxygen.found() and fs.exists('Doxyfile')
  custom_target('doc',
    command: [doxygen, files('Doxyfile')],
    output: 'reference',
    depends: need_generator ? [module_gen] : [],
    build_by_default: true,
  )
endif
