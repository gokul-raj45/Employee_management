def register_blueprints(app):
    from .auth import bp as auth_bp
    from .employees import bp as employees_bp
    from .attendance import bp as attendance_bp
    from .salaries import bp as salaries_bp
    from .leaves import bp as leaves_bp
    from .admin import bp as admin_bp
    for bp in (auth_bp, employees_bp, attendance_bp, salaries_bp, leaves_bp, admin_bp):
        app.register_blueprint(bp)
