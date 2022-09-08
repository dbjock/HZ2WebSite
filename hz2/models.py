from hz2 import db

class Rarity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Title of the rarity.
    title = db.Column(db.Text, nullable=False, unique=True)
    sortOrder = db.Column(db.Integer, unique=True)
    weapons = db.relationship('Weapon', backref='rarity', lazy=True)
    resources = db.relationship('Resource',backref='rarity', lazy=True)

    def __repr__(self):
        return f"Rarity('{self.title}')"

class Weapon_type(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False, unique=True)
    weapons = db.relationship('Weapon', backref='type', lazy=True)

    def __repr__(self):
        return f"Weapon_Type('{self.title}')"

class Weapon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('weapon_type.id'), nullable=False)
    rarity_id = db.Column(db.Integer, db.ForeignKey('rarity.id'), nullable=False)
    requirements = db.relationship('Weapon_requirement', backref='weapon',lazy=True)

    def __repr__(self):
        return f"Weapon({self.id},'{self.title},'{self.type.title}','{self.rarity.title}')"

class Resource_type(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False, unique=True)
    sortOrder = db.Column(db.Integer, unique=True)
    resources = db.relationship('Resource',backref='type', lazy=True)

    def __repr__(self):
        return f"Resource_Type('{self.title}')"

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False, unique=True)
    rarity_id = db.Column(db.Integer, db.ForeignKey('rarity.id'), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('resource_type.id'), nullable=False)
    requirements = db.relationship('Weapon_requirement', backref='resource', lazy=True)

    def __repr__(self):
        return f"Resource('{self.title}', '{self.rarity.title}', '{self.type.title}')"

class Weapon_requirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Amount of the resource need to upgrade to level
    amt_required = db.Column(db.Integer, nullable=False)
    level = db.Column(db.Integer, nullable=False)
    weapon_id = db.Column(db.Integer, db.ForeignKey('weapon.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)

    def __repr__(self):
        return f"Weapon_requirement('{self.weapon_id}','{self.level}','{self.resource.title}','{self.resource.type.title}','{self.resource.rarity.title}','{self.amt_required}')"
