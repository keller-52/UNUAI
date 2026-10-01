#import "PythonRuntime.h"
#include <Python/Python.h>

NSString *PaperAIStartBackend(NSString *dataDirectory) {
    @autoreleasepool {
        NSString *bundle=NSBundle.mainBundle.resourcePath;
        setenv("PAPER_AI_DATA_DIR",dataDirectory.UTF8String,1);
        NSString *certificates=[bundle stringByAppendingPathComponent:@"app/ca-bundle.pem"];
        setenv("SSL_CERT_FILE",certificates.UTF8String,1);
        PyPreConfig pre;
        PyPreConfig_InitIsolatedConfig(&pre);pre.utf8_mode=1;pre.configure_locale=1;
        PyStatus status=Py_PreInitialize(&pre);
        if(PyStatus_Exception(status)){NSLog(@"Python pre-initialization failed: %s",status.err_msg);return nil;}
        PyConfig config;
        PyConfig_InitIsolatedConfig(&config);
        config.buffered_stdio=0;config.write_bytecode=0;config.install_signal_handlers=0;
        config.module_search_paths_set=1;
        NSString *home=[bundle stringByAppendingPathComponent:@"python"];
        status=PyConfig_SetBytesString(&config,&config.home,home.UTF8String);
        NSArray *paths=@[[home stringByAppendingPathComponent:@"lib/python3.13"],
                         [home stringByAppendingPathComponent:@"lib/python3.13/lib-dynload"],
                         [bundle stringByAppendingPathComponent:@"app"]];
        for(NSString *path in paths){
            wchar_t *wide=Py_DecodeLocale(path.UTF8String,NULL);
            status=PyWideStringList_Append(&config.module_search_paths,wide);PyMem_RawFree(wide);
            if(PyStatus_Exception(status)){PyConfig_Clear(&config);return nil;}
        }
        status=Py_InitializeFromConfig(&config);PyConfig_Clear(&config);
        if(PyStatus_Exception(status)){NSLog(@"Python initialization failed: %s",status.err_msg);return nil;}
        PyObject *module=PyImport_ImportModule("mobile_runtime");
        if(module==NULL){PyErr_Print();PyEval_SaveThread();return nil;}
        PyObject *result=PyObject_CallMethod(module,"start","s",dataDirectory.UTF8String);
        NSString *url=nil;
        if(result){const char *value=PyUnicode_AsUTF8(result);if(value)url=[NSString stringWithUTF8String:value];Py_DECREF(result);}
        else PyErr_Print();
        Py_DECREF(module);PyEval_SaveThread();
        return url;
    }
}
