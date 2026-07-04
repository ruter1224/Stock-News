# Chaquopy
-keep class com.chaquo.python.** { *; }
-keep class * extends com.chaquo.python.PyObject { *; }

# Flask
-keep class flask.** { *; }
-keep class werkzeug.** { *; }
-keep class jinja2.** { *; }
-keep class markupsafe.** { *; }
-keep class click.** { *; }
-keep class itsdangerous.** { *; }

# Keep Python native methods
-keepclasseswithmembernames class * {
    native <methods>;
}
