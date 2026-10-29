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
if fs.exists('.metac/meson.site')
  site_lines = fs.read('.metac/meson.site').strip().split('\n')
  foreach line : site_lines
    if line.startswith('PYTHON = ')
      site_py = line.substring(10, -1)
    elif line.startswith('METAC_PYTHONPATH = ')
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

gen_env = environment()
if site_pythonpath != ''
  gen_env.set('PYTHONPATH', site_pythonpath)
endif

# The fragment and the sources it lists are consumed at configure time, so
# the module is brought into existence right here - when the fragment is
# missing, when the forced regeneration mode demands it, or in the auto mode
# when any of the listed sources has disappeared - mirroring the resilience
# of the cmake and scons backends
run_generator = not has_meson_file or regen_opt.enabled()
if not run_generator and regen_opt.auto() and py.found()
  foreach f : fs.read(meson_file).strip().split()
    if not fs.exists(f)
      run_generator = true
    endif
  endforeach
endif

if run_generator
  if not py.found()
    error('MetaC generator requires Python 3, but Python was not found and ' + meson_file + ' is missing or the sources it lists have disappeared.')
  endif
  message((has_meson_file ? 'Regenerating' : 'Bootstrapping') + ' MetaC module ' + module_name)
  run_command(py, module_name + '.py', module_name, '--backend=meson', env: gen_env, check: true)
endif

metac_file_names = fs.read(meson_file).strip().split()

# Reading every generated file registers it as a configure dependency so that
# ninja reruns this setup whenever the files appear, change or disappear -
# the meson equivalent of cmake's CMAKE_CONFIGURE_DEPENDS - which is what
# lets the configure-time regeneration above bring the deleted sources back
foreach f : metac_file_names
  fs.read(f)
endforeach

metac_sources = files(metac_file_names)

need_generator = regen_opt.enabled() or (regen_opt.auto() and py.found())

if need_generator
  stamp_file = meson.current_build_dir() / (module_name + '.stamp')
  module_gen = custom_target(
    module_name + '-generate',
    input: module_name + '.py',
    output: module_name + '.stamp',
    command: [py, '@INPUT@', module_name, '--backend=meson', stamp_file],
    env: gen_env,
    build_by_default: true,
  )
  metac_dep = declare_dependency(
    sources: [metac_sources, module_gen],
    include_directories: include_directories('.')
  )
else
  metac_dep = declare_dependency(
    sources: metac_sources,
    include_directories: include_directories('.')
  )
endif

app_sources = []
if fs.exists('@project@.c')
  app_sources += files('@project@.c')
endif

has_c_sources = false
foreach f : metac_file_names
  if f.endswith('.c')
    has_c_sources = true
  endif
endforeach

if app_sources.length() > 0 or has_c_sources
  exe = executable('@project@',
    sources: app_sources,
    dependencies: [metac_dep]
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
